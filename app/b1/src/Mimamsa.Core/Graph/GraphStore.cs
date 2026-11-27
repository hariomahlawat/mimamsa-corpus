// C15 WP3: PostgreSQL graph storage (ADR-0006). Nodes and typed edges are stored per generation; a generation's graph
// is published atomically (one transaction, then a graph_generation row with counts and a content digest), so a crash
// mid-publication leaves nothing visible and the next start publishes again. Review state lives in its own table and
// is never written by the builder. Every query takes the set of documents that are NOT visible (withdrawn, ineligible)
// and drops any node naming such a document and any edge whose source or endpoint is hidden.
using Npgsql;
using NpgsqlTypes;

namespace Mimamsa.Core.Graph;

public sealed record EdgeView(GraphEdge Edge, GraphNode FromNode, GraphNode ToNode);
public sealed record GraphPath(IReadOnlyList<string> Nodes, IReadOnlyList<EdgeView> Edges);
public sealed record GraphStats(IReadOnlyDictionary<string, long> NodesByKind, IReadOnlyDictionary<string, long> EdgesByType,
                                IReadOnlyDictionary<string, long> EdgesByVerification, long Nodes, long Edges);

public sealed class GraphNotPublishedException(string gen) : Exception($"graph for generation {gen} is not published");

public sealed class GraphStore(NpgsqlDataSource db)
{
    public const int MaxDepth = 4, MaxFrontier = 5000, MaxEdges = 2000, MaxPathEdgesPerLevel = 10_000;

    public async Task EnsureSchemaAsync()
    {
        await using var c = await db.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand("""
            CREATE TABLE IF NOT EXISTS graph_generation(
              generation_id text PRIMARY KEY, builder_version text NOT NULL, node_count int NOT NULL, edge_count int NOT NULL,
              content_digest text NOT NULL, published_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS graph_nodes(
              generation_id text NOT NULL, node_id text NOT NULL, kind text NOT NULL, label text NOT NULL, doc_id text, copy_sha text,
              held boolean NOT NULL, page int, family text, code text, PRIMARY KEY (generation_id, node_id));
            CREATE TABLE IF NOT EXISTS graph_edges(
              generation_id text NOT NULL, edge_id text NOT NULL, type text NOT NULL, from_node text NOT NULL, to_node text NOT NULL,
              origin text NOT NULL, source_doc_id text, source_copy_sha text, page int, quote text,
              temporal_from text, temporal_from_status text NOT NULL, temporal_to text, temporal_to_status text NOT NULL,
              verification text NOT NULL, review_state text NOT NULL, uncertainty text NOT NULL, has_legal_effect boolean NOT NULL,
              PRIMARY KEY (generation_id, edge_id),
              CONSTRAINT graph_edge_builder_verification CHECK (verification IN ('CANDIDATE','EXTRACTED_STRUCTURE','CURATED_NAVIGATION','DOCUMENTARY_CHECKED','LEGAL_REVIEWED')));
            CREATE INDEX IF NOT EXISTS graph_edges_from ON graph_edges(generation_id, from_node);
            CREATE INDEX IF NOT EXISTS graph_edges_to ON graph_edges(generation_id, to_node);
            CREATE INDEX IF NOT EXISTS graph_edges_source ON graph_edges(generation_id, source_doc_id);
            CREATE INDEX IF NOT EXISTS graph_nodes_doc ON graph_nodes(generation_id, doc_id);
            -- review decisions are recorded only through an authorised review process (none exists at AUTH-LEDGER v0)
            CREATE TABLE IF NOT EXISTS graph_edge_reviews(
              edge_id text NOT NULL, review_state text NOT NULL, reviewer text NOT NULL, note text, at timestamptz NOT NULL DEFAULT now());
            """, c);
        await cmd.ExecuteNonQueryAsync();
    }

    public static string Digest(LegalGraph g) =>
        GraphIds.Hash(g.BuilderVersion + "|" + string.Join(",", g.Nodes.Select(n => n.Id)) + "|" + string.Join(",", g.Edges.Select(e => e.Id)));

    /// Publish the generation's graph atomically. Returns false when the identical graph is already published.
    public async Task<bool> PublishAsync(LegalGraph g, Func<Task>? beforeCommit = null)
    {
        if (g.Edges.Any(e => !Verification.BuilderValues.Contains(e.Verification)))
            throw new InvalidOperationException("the builder may not publish reviewed or verified edges");
        var digest = Digest(g);
        await using var c = await db.OpenConnectionAsync();
        await using (var q = new NpgsqlCommand("SELECT content_digest FROM graph_generation WHERE generation_id=$1", c))
        {
            q.Parameters.AddWithValue(g.GenerationId);
            if (await q.ExecuteScalarAsync() is string d && d == digest) return false;
        }
        await using var tx = await c.BeginTransactionAsync();
        await using (var lk = new NpgsqlCommand("SELECT pg_advisory_xact_lock(hashtext('mimamsa_graph_publish'))", c, tx)) await lk.ExecuteNonQueryAsync();
        foreach (var t in new[] { "graph_generation", "graph_edges", "graph_nodes" })
            await using (var del = new NpgsqlCommand($"DELETE FROM {t} WHERE generation_id=$1", c, tx)) { del.Parameters.AddWithValue(g.GenerationId); await del.ExecuteNonQueryAsync(); }
        await using (var w = await c.BeginBinaryImportAsync("COPY graph_nodes (generation_id,node_id,kind,label,doc_id,copy_sha,held,page,family,code) FROM STDIN (FORMAT BINARY)"))
        {
            foreach (var n in g.Nodes)
            {
                await w.StartRowAsync();
                await w.WriteAsync(g.GenerationId); await w.WriteAsync(n.Id); await w.WriteAsync(n.Kind); await w.WriteAsync(n.Label);
                await W(w, n.DocId); await W(w, n.CopySha); await w.WriteAsync(n.Held); await W(w, n.Page); await W(w, n.Family); await W(w, n.Code);
            }
            await w.CompleteAsync();
        }
        await using (var w = await c.BeginBinaryImportAsync("COPY graph_edges (generation_id,edge_id,type,from_node,to_node,origin,source_doc_id,source_copy_sha,page,quote,temporal_from,temporal_from_status,temporal_to,temporal_to_status,verification,review_state,uncertainty,has_legal_effect) FROM STDIN (FORMAT BINARY)"))
        {
            foreach (var e in g.Edges)
            {
                await w.StartRowAsync();
                await w.WriteAsync(g.GenerationId); await w.WriteAsync(e.Id); await w.WriteAsync(e.Type); await w.WriteAsync(e.From); await w.WriteAsync(e.To);
                await w.WriteAsync(e.Origin); await W(w, e.SourceDocId); await W(w, e.SourceCopySha); await W(w, e.Page); await W(w, e.Quote);
                await W(w, e.TemporalFrom); await w.WriteAsync(e.TemporalFromStatus); await W(w, e.TemporalTo); await w.WriteAsync(e.TemporalToStatus);
                await w.WriteAsync(e.Verification); await w.WriteAsync(e.ReviewState); await w.WriteAsync(e.Uncertainty); await w.WriteAsync(e.HasLegalEffect);
            }
            await w.CompleteAsync();
        }
        if (beforeCommit is not null) await beforeCommit();     // test hook: a failure here must leave the previous state intact
        await using (var ins = new NpgsqlCommand("INSERT INTO graph_generation(generation_id,builder_version,node_count,edge_count,content_digest) VALUES ($1,$2,$3,$4,$5)", c, tx))
        {
            ins.Parameters.AddWithValue(g.GenerationId); ins.Parameters.AddWithValue(g.BuilderVersion); ins.Parameters.AddWithValue(g.Nodes.Count);
            ins.Parameters.AddWithValue(g.Edges.Count); ins.Parameters.AddWithValue(digest);
            await ins.ExecuteNonQueryAsync();
        }
        await tx.CommitAsync();
        _statsCache.Clear();
        return true;
    }

    static Task W(NpgsqlBinaryImporter w, string? v) => v is null ? w.WriteNullAsync() : w.WriteAsync(v, NpgsqlDbType.Text);
    static Task W(NpgsqlBinaryImporter w, int? v) => v is null ? w.WriteNullAsync() : w.WriteAsync(v.Value, NpgsqlDbType.Integer);

    /// Integrity check: the published row counts and digest match the stored rows and the expected graph.
    public async Task<(bool ok, string detail)> VerifyAsync(LegalGraph expected)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("""
            SELECT gg.node_count, gg.edge_count, gg.content_digest,
                   (SELECT count(*) FROM graph_nodes WHERE generation_id=$1), (SELECT count(*) FROM graph_edges WHERE generation_id=$1)
            FROM graph_generation gg WHERE gg.generation_id=$1
            """, c);
        q.Parameters.AddWithValue(expected.GenerationId);
        await using var r = await q.ExecuteReaderAsync();
        if (!await r.ReadAsync()) return (false, "not published");
        var (nc, ec, dg, rn, re) = (r.GetInt32(0), r.GetInt32(1), r.GetString(2), r.GetInt64(3), r.GetInt64(4));
        if (nc != rn || ec != re) return (false, $"row counts differ from the published counts ({rn}/{nc} nodes, {re}/{ec} edges)");
        if (dg != Digest(expected)) return (false, "content digest differs from the generation's graph");
        return (true, $"{nc} nodes, {ec} edges, digest {dg[..12]}");
    }

    async Task RequirePublished(NpgsqlConnection c, string gen)
    {
        await using var q = new NpgsqlCommand("SELECT 1 FROM graph_generation WHERE generation_id=$1", c);
        q.Parameters.AddWithValue(gen);
        if (await q.ExecuteScalarAsync() is null) throw new GraphNotPublishedException(gen);
    }

    const string NodeCols = "node_id,kind,label,doc_id,copy_sha,held,page,family,code";
    static GraphNode ReadNode(NpgsqlDataReader r, int o) => new(r.GetString(o), r.GetString(o + 1), r.GetString(o + 2), S(r, o + 3), S(r, o + 4),
        r.GetBoolean(o + 5), r.IsDBNull(o + 6) ? null : r.GetInt32(o + 6), S(r, o + 7), S(r, o + 8));
    static string? S(NpgsqlDataReader r, int i) => r.IsDBNull(i) ? null : r.GetString(i);
    /// A node with its own document is visible when that document is. A node without one (an unresolved reference,
    /// whose label is text from the citing judgment) is visible only while at least one visible edge touches it (a node with no edges at all is structural and stays), so a
    /// withdrawal hides it on lookup and in the statistics too (C15 security review L3).
    const string Hidden = """
        ((n.doc_id IS NOT NULL AND NOT n.doc_id = ANY($2)) OR (n.doc_id IS NULL AND (
            NOT EXISTS (SELECT 1 FROM graph_edges e WHERE e.generation_id=n.generation_id AND (e.from_node=n.node_id OR e.to_node=n.node_id))
         OR 
            EXISTS (SELECT 1 FROM graph_edges e JOIN graph_nodes o ON o.generation_id=e.generation_id AND o.node_id=e.to_node
                    WHERE e.generation_id=n.generation_id AND e.from_node=n.node_id
                      AND (e.source_doc_id IS NULL OR NOT e.source_doc_id = ANY($2)) AND (o.doc_id IS NULL OR NOT o.doc_id = ANY($2)))
         OR EXISTS (SELECT 1 FROM graph_edges e JOIN graph_nodes o ON o.generation_id=e.generation_id AND o.node_id=e.from_node
                    WHERE e.generation_id=n.generation_id AND e.to_node=n.node_id
                      AND (e.source_doc_id IS NULL OR NOT e.source_doc_id = ANY($2)) AND (o.doc_id IS NULL OR NOT o.doc_id = ANY($2))))))
        """;

    public async Task<GraphNode?> NodeAsync(string gen, string nodeId, string[] hidden)
    {
        await using var c = await db.OpenConnectionAsync();
        await RequirePublished(c, gen);
        await using var q = new NpgsqlCommand($"SELECT {NodeCols} FROM graph_nodes n WHERE n.generation_id=$1 AND {Hidden} AND n.node_id=$3", c);
        q.Parameters.AddWithValue(gen); q.Parameters.AddWithValue(hidden); q.Parameters.AddWithValue(nodeId);
        await using var r = await q.ExecuteReaderAsync();
        return await r.ReadAsync() ? ReadNode(r, 0) : null;
    }

    /// Visible edges incident to any node of the frontier (one indexed lookup per level).
    async Task<List<EdgeView>> ExpandAsync(NpgsqlConnection c, string gen, string[] frontier, string[] hidden, int limit, string[]? exclude = null)
    {
        await using var q = new NpgsqlCommand($"""
            SELECT e.edge_id,e.type,e.from_node,e.to_node,e.origin,e.source_doc_id,e.source_copy_sha,e.page,e.quote,e.temporal_from,e.temporal_from_status,
                   e.temporal_to,e.temporal_to_status,e.verification,e.review_state,e.uncertainty,e.has_legal_effect,
                   a.node_id,a.kind,a.label,a.doc_id,a.copy_sha,a.held,a.page,a.family,a.code,
                   b.node_id,b.kind,b.label,b.doc_id,b.copy_sha,b.held,b.page,b.family,b.code
            FROM graph_edges e
            JOIN graph_nodes a ON a.generation_id=e.generation_id AND a.node_id=e.from_node
            JOIN graph_nodes b ON b.generation_id=e.generation_id AND b.node_id=e.to_node
            WHERE e.generation_id=$1 AND (e.from_node = ANY($3) OR e.to_node = ANY($3))
              AND (e.source_doc_id IS NULL OR NOT e.source_doc_id = ANY($2))
              AND (a.doc_id IS NULL OR NOT a.doc_id = ANY($2)) AND (b.doc_id IS NULL OR NOT b.doc_id = ANY($2))
              AND NOT e.edge_id = ANY($5)
            ORDER BY e.type, e.edge_id
            LIMIT $4
            """, c);
        q.Parameters.AddWithValue(gen); q.Parameters.AddWithValue(hidden); q.Parameters.AddWithValue(frontier); q.Parameters.AddWithValue(limit);
        q.Parameters.AddWithValue(exclude ?? Array.Empty<string>());
        var list = new List<EdgeView>();
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync())
            list.Add(new EdgeView(new GraphEdge(r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3), r.GetString(4), S(r, 5), S(r, 6),
                r.IsDBNull(7) ? null : r.GetInt32(7), S(r, 8), S(r, 9), r.GetString(10), S(r, 11), r.GetString(12), r.GetString(13), r.GetString(14),
                r.GetString(15), r.GetBoolean(16)), ReadNode(r, 17), ReadNode(r, 26)));
        return list;
    }

    public async Task<(GraphNode? node, IReadOnlyList<EdgeView> edges, bool truncated)> NeighbourhoodAsync(string gen, string nodeId, int depth, string[] hidden, int limit = 500)
    {
        depth = Math.Clamp(depth, 1, 2); limit = Math.Clamp(limit, 1, MaxEdges);
        await using var c = await db.OpenConnectionAsync();
        await RequirePublished(c, gen);
        GraphNode? node;
        await using (var q = new NpgsqlCommand($"SELECT {NodeCols} FROM graph_nodes n WHERE n.generation_id=$1 AND {Hidden} AND n.node_id=$3", c))
        {
            q.Parameters.AddWithValue(gen); q.Parameters.AddWithValue(hidden); q.Parameters.AddWithValue(nodeId);
            await using var r = await q.ExecuteReaderAsync();
            node = await r.ReadAsync() ? ReadNode(r, 0) : null;
        }
        if (node is null) return (null, Array.Empty<EdgeView>(), false);
        var seen = new HashSet<string> { nodeId }; var frontier = new[] { nodeId };
        var result = new Dictionary<string, EdgeView>();
        bool truncated = false;
        for (int d = 0; d < depth && frontier.Length > 0; d++)
        {
            // edges already collected are excluded before the limit applies (Codex review of PR #75): a deeper level's
            // re-returned first-level edges must not crowd out new ones or report truncation that did not happen
            var got = await ExpandAsync(c, gen, frontier, hidden, limit - result.Count + 1, result.Keys.ToArray());
            if (result.Count + got.Count > limit) { truncated = true; got = got.Take(limit - result.Count).ToList(); }
            foreach (var e in got) result.TryAdd(e.Edge.Id, e);
            frontier = got.SelectMany(e => new[] { e.Edge.From, e.Edge.To }).Where(seen.Add).Take(MaxFrontier).ToArray();
            if (truncated) break;
        }
        return (node, result.Values.ToList(), truncated);
    }

    /// Shortest visible path (undirected) of at most maxDepth edges, by level-wise expansion from the source.
    public async Task<GraphPath?> PathAsync(string gen, string from, string to, int maxDepth, string[] hidden)
    {
        maxDepth = Math.Clamp(maxDepth, 1, MaxDepth);
        await using var c = await db.OpenConnectionAsync();
        await RequirePublished(c, gen);
        if (from == to) return new GraphPath(new[] { from }, Array.Empty<EdgeView>());
        var parent = new Dictionary<string, EdgeView?> { [from] = null };
        var frontier = new[] { from };
        for (int d = 0; d < maxDepth && frontier.Length > 0; d++)
        {
            var next = new List<string>();
            var inFrontier = new HashSet<string>(frontier, StringComparer.Ordinal);
            // C15 security review L5: bounded per level (was 50,000) so one path request cannot pull a large share of the graph
            foreach (var e in await ExpandAsync(c, gen, frontier, hidden, MaxPathEdgesPerLevel))
                foreach (var (a, b) in new[] { (e.Edge.From, e.Edge.To), (e.Edge.To, e.Edge.From) })
                    if (inFrontier.Contains(a) && !parent.ContainsKey(b)) { parent[b] = e; next.Add(b); }
            if (parent.ContainsKey(to))
            {
                var nodes = new List<string> { to }; var edges = new List<EdgeView>();
                for (var cur = to; parent[cur] is { } pe; ) { edges.Add(pe); cur = pe.Edge.From == cur ? pe.Edge.To : pe.Edge.From; nodes.Add(cur); }
                nodes.Reverse(); edges.Reverse();
                return new GraphPath(nodes, edges);
            }
            frontier = next.Take(MaxFrontier).ToArray();
        }
        return null;
    }

    // Statistics depend only on (generation, hidden set); they are cached per exact hidden set, so a withdrawal (a new
    // hidden set) is never answered from a stale entry. Bounded: cleared when it grows past 32 entries.
    readonly System.Collections.Concurrent.ConcurrentDictionary<string, GraphStats> _statsCache = new();

    public async Task<GraphStats> StatsAsync(string gen, string[] hidden)
    {
        var key = gen + "|" + string.Join(",", hidden.OrderBy(h => h, StringComparer.Ordinal));
        if (_statsCache.TryGetValue(key, out var cached)) return cached;
        var s = await StatsUncachedAsync(gen, hidden);
        if (_statsCache.Count > 32) _statsCache.Clear();
        _statsCache[key] = s;
        return s;
    }

    async Task<GraphStats> StatsUncachedAsync(string gen, string[] hidden)
    {
        await using var c = await db.OpenConnectionAsync();
        await RequirePublished(c, gen);
        async Task<Dictionary<string, long>> Group(string sql)
        {
            await using var q = new NpgsqlCommand(sql, c);
            q.Parameters.AddWithValue(gen); q.Parameters.AddWithValue(hidden);
            var d = new Dictionary<string, long>();
            await using var r = await q.ExecuteReaderAsync();
            while (await r.ReadAsync()) d[r.GetString(0)] = r.GetInt64(1);
            return d;
        }
        const string visibleEdges = """
            FROM graph_edges e JOIN graph_nodes a ON a.generation_id=e.generation_id AND a.node_id=e.from_node
            JOIN graph_nodes b ON b.generation_id=e.generation_id AND b.node_id=e.to_node
            WHERE e.generation_id=$1 AND (e.source_doc_id IS NULL OR NOT e.source_doc_id = ANY($2))
              AND (a.doc_id IS NULL OR NOT a.doc_id = ANY($2)) AND (b.doc_id IS NULL OR NOT b.doc_id = ANY($2))
            """;
        var nodes = await Group($"SELECT kind, count(*) FROM graph_nodes n WHERE n.generation_id=$1 AND {Hidden} GROUP BY kind");
        var types = await Group($"SELECT e.type, count(*) {visibleEdges} GROUP BY e.type");
        var ver = await Group($"SELECT e.verification, count(*) {visibleEdges} GROUP BY e.verification");
        return new GraphStats(nodes, types, ver, nodes.Values.Sum(), types.Values.Sum());
    }
}
