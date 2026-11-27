// C15 WP6: Document Studio foundation. Per-user private working documents (WORKING_DOCUMENT_PROCESSING): they never
// become shared sources, search entries, graph evidence or templates. Every query is scoped by owner, so a document
// that belongs to someone else is indistinguishable from one that does not exist (the API answers 404). Admin capacity
// gives no access to other users' documents (DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY §2).
//
// Body model: an ordered list of blocks. Each block has an ORIGIN that the reader can always see:
//   user        text the user wrote (or edited);
//   template    a section heading from a generic, non-legal skeleton;
//   suggestion  automated text (e.g. "questions requiring legal review" from the Commander workspace), until edited;
//   corpus      a citation or quotation of the published library. Only its REFERENCE is stored (doc, copy, page,
//               passage); the citation and quoted text are produced at read time from the current, eligible copy, so a
//               withdrawn source is shown as "source no longer available" and its text is never stored or exported.
// "Review" states are the user's own workflow labels; nothing here is, or records, legal approval.
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace Mimamsa.Core.Studio;

public sealed record StudioDocSummary(string Id, string Title, string Template, string State, int Version, DateTime UpdatedAt, int Bytes);
public sealed record StudioVersion(int Version, string State, DateTime CreatedAt, int Bytes);
public sealed record StudioDoc(string Id, string Title, string Template, string State, int Version, DateTime CreatedAt, DateTime UpdatedAt, JsonArray Blocks);
public sealed record StudioNote(string Id, string Text, string? RefDoc, string? RefCopy, int? RefPage, DateTime CreatedAt);

public sealed class StudioValidationException(string message) : Exception(message);

public sealed class StudioStore(NpgsqlDataSource db)
{
    public const int MaxTitle = 200, MaxBlocks = 400, MaxText = 20_000, MaxBodyBytes = 60_000, MaxDocsPerUser = 500, MaxVersionsPerDoc = 200,
                     MaxNotesPerUser = 2000, MaxNoteText = 4000;
    public static readonly string[] States = { "draft", "in_review", "final_draft" };
    public static readonly string[] Origins = { "user", "template", "suggestion", "corpus" };
    public static readonly string[] Types = { "heading", "text", "question", "citation", "quote" };

    /// Generic skeletons only. No legal form is offered: none in this library is verified or approved
    /// (FORM_DISCOVERY_AND_COVERAGE_REGISTER), so templates are clearly marked as non-legal working structures.
    public static readonly IReadOnlyDictionary<string, (string label, string[] headings)> Templates = new Dictionary<string, (string, string[])>
    {
        ["blank"] = ("Blank document", Array.Empty<string>()),
        ["research-note"] = ("Research note (generic skeleton, not a legal form)",
            new[] { "Question researched", "Sources found", "What the sources say (quoted with citations)", "Open points and questions requiring legal review" }),
        ["memo"] = ("Internal memo (generic skeleton, not a legal form)",
            new[] { "Purpose", "Facts as known (user-supplied, unverified)", "Relevant provisions and authorities", "Questions requiring legal review", "Recommended next step for a competent authority" }),
    };

    public async Task EnsureSchemaAsync()
    {
        await using var c = await db.OpenConnectionAsync();
        await using var cmd = new NpgsqlCommand("""
            CREATE TABLE IF NOT EXISTS studio_documents(
              doc_id text PRIMARY KEY, owner text NOT NULL, title text NOT NULL, template text NOT NULL,
              state text NOT NULL DEFAULT 'draft', version int NOT NULL DEFAULT 0,
              created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
            CREATE INDEX IF NOT EXISTS studio_documents_owner ON studio_documents(owner, updated_at DESC);
            CREATE TABLE IF NOT EXISTS studio_versions(
              doc_id text NOT NULL REFERENCES studio_documents(doc_id) ON DELETE CASCADE, version int NOT NULL,
              state text NOT NULL, body jsonb NOT NULL, bytes int NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
              PRIMARY KEY(doc_id, version));
            CREATE TABLE IF NOT EXISTS studio_notes(
              note_id text PRIMARY KEY, owner text NOT NULL, text text NOT NULL,
              ref_doc text, ref_copy text, ref_page int, created_at timestamptz NOT NULL DEFAULT now());
            CREATE INDEX IF NOT EXISTS studio_notes_owner ON studio_notes(owner, created_at DESC);
            """, c);
        await cmd.ExecuteNonQueryAsync();
    }

    static string NewId(string prefix) => prefix + Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(12)).ToLowerInvariant();

    // ------------------------------------------------------------------ validation
    static string Str(JsonNode? n) => n is JsonValue v && v.TryGetValue<string>(out var s) ? s : "";

    /// Normalise and validate a client body. Corpus blocks keep only their reference fields (any text the client sends
    /// for them is discarded); other blocks keep only their text. Throws StudioValidationException with a plain reason.
    public static JsonArray Normalise(JsonNode? body)
    {
        if (body is not JsonArray arr) throw new StudioValidationException("The document body must be a list of blocks.");
        if (arr.Count > MaxBlocks) throw new StudioValidationException($"A document may have at most {MaxBlocks} blocks.");
        var outp = new JsonArray();
        foreach (var n in arr)
        {
            if (n is not JsonObject b) throw new StudioValidationException("Each block must be an object.");
            var type = Str(b["type"]); var origin = Str(b["origin"]);
            if (!Types.Contains(type)) throw new StudioValidationException($"Unknown block type '{type}'.");
            if (type is "citation" or "quote")
            {
                var doc = Str(b["doc_id"]); var copy = Str(b["copy"]); var page = b["page"] is JsonValue pv && pv.TryGetValue<int>(out var pg) ? pg : 0;
                if (doc.Length is 0 or > 200 || copy.Length != 12 || !copy.All(Uri.IsHexDigit) || page < 1)
                    throw new StudioValidationException("A citation must name a document, a 12-character copy hash and a page.");
                var o = new JsonObject { ["type"] = type, ["origin"] = "corpus", ["doc_id"] = doc, ["copy"] = copy.ToLowerInvariant(), ["page"] = page };
                if (type == "quote")
                {
                    var passage = Str(b["passage_id"]);
                    if (passage.Length is 0 or > 64) throw new StudioValidationException("A quotation must name a passage of the held text.");
                    o["passage_id"] = passage;
                }
                var para = Str(b["para"]); if (para.Length is > 0 and <= 32) o["para"] = para;
                outp.Add(o);
            }
            else
            {
                if (origin is "corpus" || !Origins.Contains(origin)) throw new StudioValidationException("A text block's origin must be user, template or suggestion.");
                var text = Str(b["text"]);
                if (text.Length > MaxText) throw new StudioValidationException($"A block may hold at most {MaxText:N0} characters.");
                outp.Add(new JsonObject { ["type"] = type, ["origin"] = origin, ["text"] = text });
            }
        }
        if (JsonSerializer.SerializeToUtf8Bytes(outp).Length > MaxBodyBytes) throw new StudioValidationException($"The document is larger than {MaxBodyBytes / 1000} kB.");
        return outp;
    }

    static string Title(string? t)
    {
        t = (t ?? "").Trim();
        if (t.Length == 0) throw new StudioValidationException("A title is required.");
        if (t.Length > MaxTitle) throw new StudioValidationException($"The title may have at most {MaxTitle} characters.");
        return t;
    }

    // ------------------------------------------------------------------ documents
    public async Task<StudioDoc> CreateAsync(string owner, string? title, string template)
    {
        if (!Templates.TryGetValue(template, out var tpl)) throw new StudioValidationException("Unknown template.");
        var t = Title(title);
        var blocks = new JsonArray(tpl.headings.Select(hd => (JsonNode)new JsonObject { ["type"] = "heading", ["origin"] = "template", ["text"] = hd }).ToArray());
        var id = NewId("sd-");
        await using var c = await db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        await LockOwnerAsync(c, tx, owner);
        await using (var q = new NpgsqlCommand("SELECT count(*) FROM studio_documents WHERE owner=$1", c, tx))
        {
            q.Parameters.AddWithValue(owner);
            if ((long)(await q.ExecuteScalarAsync())! >= MaxDocsPerUser) throw new StudioValidationException($"At most {MaxDocsPerUser} documents per user.");
        }
        await using (var ins = new NpgsqlCommand("INSERT INTO studio_documents(doc_id, owner, title, template, version) VALUES ($1,$2,$3,$4,1)", c, tx))
        { ins.Parameters.AddWithValue(id); ins.Parameters.AddWithValue(owner); ins.Parameters.AddWithValue(t); ins.Parameters.AddWithValue(template); await ins.ExecuteNonQueryAsync(); }
        await InsertVersionAsync(c, tx, id, 1, "draft", blocks);
        await tx.CommitAsync();
        return (await GetAsync(owner, id))!;
    }

    /// C15 security review L5: per-owner caps are count-then-insert; a transaction-scoped advisory lock on the owner
    /// serialises that owner's creates so parallel requests cannot exceed the cap.
    static async Task LockOwnerAsync(NpgsqlConnection c, NpgsqlTransaction tx, string owner)
    {
        await using var l = new NpgsqlCommand("SELECT pg_advisory_xact_lock(hashtext('studio:' || $1))", c, tx);
        l.Parameters.AddWithValue(owner);
        await l.ExecuteNonQueryAsync();
    }

    static async Task InsertVersionAsync(NpgsqlConnection c, NpgsqlTransaction tx, string id, int version, string state, JsonArray blocks)
    {
        var json = blocks.ToJsonString();
        await using var v = new NpgsqlCommand("INSERT INTO studio_versions(doc_id, version, state, body, bytes) VALUES ($1,$2,$3,$4::jsonb,$5)", c, tx);
        v.Parameters.AddWithValue(id); v.Parameters.AddWithValue(version); v.Parameters.AddWithValue(state); v.Parameters.AddWithValue(json);
        v.Parameters.AddWithValue(System.Text.Encoding.UTF8.GetByteCount(json));
        await v.ExecuteNonQueryAsync();
    }

    public async Task<IReadOnlyList<StudioDocSummary>> ListAsync(string owner)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("""
            SELECT d.doc_id, d.title, d.template, d.state, d.version, d.updated_at, v.bytes
            FROM studio_documents d JOIN studio_versions v ON v.doc_id = d.doc_id AND v.version = d.version
            WHERE d.owner = $1 ORDER BY d.updated_at DESC LIMIT 500
            """, c);
        q.Parameters.AddWithValue(owner);
        var list = new List<StudioDocSummary>();
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync()) list.Add(new(r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3), r.GetInt32(4), r.GetDateTime(5), r.GetInt32(6)));
        return list;
    }

    /// The document at its current version, or at `version` when given; null when it does not exist FOR THIS OWNER.
    public async Task<StudioDoc?> GetAsync(string owner, string id, int? version = null)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("""
            SELECT d.doc_id, d.title, d.template, v.state, v.version, d.created_at, d.updated_at, v.body::text
            FROM studio_documents d JOIN studio_versions v ON v.doc_id = d.doc_id AND v.version = COALESCE($3, d.version)
            WHERE d.owner = $1 AND d.doc_id = $2
            """, c);
        q.Parameters.AddWithValue(owner); q.Parameters.AddWithValue(id); q.Parameters.AddWithValue((object?)version ?? DBNull.Value);
        await using var r = await q.ExecuteReaderAsync();
        if (!await r.ReadAsync()) return null;
        return new StudioDoc(r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3), r.GetInt32(4), r.GetDateTime(5), r.GetDateTime(6),
                             JsonNode.Parse(r.GetString(7)) as JsonArray ?? new JsonArray());
    }

    /// Save a new version (optimistic concurrency on `baseVersion`). Returns null when the document does not exist for
    /// this owner; throws StudioConflictException when someone saved a newer version first (e.g. another tab).
    public async Task<StudioDoc?> SaveAsync(string owner, string id, int baseVersion, string? title, string state, JsonArray blocks)
    {
        if (!States.Contains(state)) throw new StudioValidationException("Unknown state.");
        var t = Title(title);
        await using var c = await db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        int current;
        await using (var q = new NpgsqlCommand("SELECT version FROM studio_documents WHERE owner=$1 AND doc_id=$2 FOR UPDATE", c, tx))
        {
            q.Parameters.AddWithValue(owner); q.Parameters.AddWithValue(id);
            var o = await q.ExecuteScalarAsync();
            if (o is null) return null;
            current = (int)o;
        }
        if (current != baseVersion) throw new StudioConflictException(current);
        if (current >= MaxVersionsPerDoc) throw new StudioValidationException($"At most {MaxVersionsPerDoc} versions per document; export it and start a new one.");
        await InsertVersionAsync(c, tx, id, current + 1, state, blocks);
        await using (var u = new NpgsqlCommand("UPDATE studio_documents SET version=$3, title=$4, state=$5, updated_at=now() WHERE owner=$1 AND doc_id=$2", c, tx))
        { u.Parameters.AddWithValue(owner); u.Parameters.AddWithValue(id); u.Parameters.AddWithValue(current + 1); u.Parameters.AddWithValue(t); u.Parameters.AddWithValue(state); await u.ExecuteNonQueryAsync(); }
        await tx.CommitAsync();
        return await GetAsync(owner, id);
    }

    public async Task<IReadOnlyList<StudioVersion>?> VersionsAsync(string owner, string id)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("""
            SELECT v.version, v.state, v.created_at, v.bytes FROM studio_versions v JOIN studio_documents d ON d.doc_id = v.doc_id
            WHERE d.owner = $1 AND d.doc_id = $2 ORDER BY v.version DESC
            """, c);
        q.Parameters.AddWithValue(owner); q.Parameters.AddWithValue(id);
        var list = new List<StudioVersion>();
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync()) list.Add(new(r.GetInt32(0), r.GetString(1), r.GetDateTime(2), r.GetInt32(3)));
        if (list.Count == 0) return null;
        return list;
    }

    /// Hard delete of the user's own document and all its versions (working content is not retained after deletion).
    public async Task<bool> DeleteAsync(string owner, string id)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("DELETE FROM studio_documents WHERE owner=$1 AND doc_id=$2", c);
        q.Parameters.AddWithValue(owner); q.Parameters.AddWithValue(id);
        return await q.ExecuteNonQueryAsync() > 0;
    }

    // ------------------------------------------------------------------ research notes
    public async Task<StudioNote> AddNoteAsync(string owner, string? text, string? refDoc, string? refCopy, int? refPage)
    {
        text = (text ?? "").Trim();
        if (text.Length == 0) throw new StudioValidationException("A note cannot be empty.");
        if (text.Length > MaxNoteText) throw new StudioValidationException($"A note may hold at most {MaxNoteText:N0} characters.");
        if (refDoc is not null && (refDoc.Length > 200 || refCopy is null || refCopy.Length != 12 || !refCopy.All(Uri.IsHexDigit) || refPage is null or < 1))
            throw new StudioValidationException("A note's reference must name a document, a 12-character copy hash and a page.");
        var id = NewId("sn-");
        await using var c = await db.OpenConnectionAsync();
        await using var tx = await c.BeginTransactionAsync();
        await LockOwnerAsync(c, tx, owner);
        await using (var q = new NpgsqlCommand("SELECT count(*) FROM studio_notes WHERE owner=$1", c, tx))
        {
            q.Parameters.AddWithValue(owner);
            if ((long)(await q.ExecuteScalarAsync())! >= MaxNotesPerUser) throw new StudioValidationException($"At most {MaxNotesPerUser} notes per user.");
        }
        await using var ins = new NpgsqlCommand("INSERT INTO studio_notes(note_id, owner, text, ref_doc, ref_copy, ref_page) VALUES ($1,$2,$3,$4,$5,$6) RETURNING created_at", c, tx);
        ins.Parameters.AddWithValue(id); ins.Parameters.AddWithValue(owner); ins.Parameters.AddWithValue(text);
        ins.Parameters.AddWithValue((object?)refDoc ?? DBNull.Value); ins.Parameters.AddWithValue((object?)refCopy?.ToLowerInvariant() ?? DBNull.Value);
        ins.Parameters.AddWithValue((object?)refPage ?? DBNull.Value);
        var at = (DateTime)(await ins.ExecuteScalarAsync())!;
        await tx.CommitAsync();
        return new StudioNote(id, text, refDoc, refCopy?.ToLowerInvariant(), refPage, at);
    }

    public async Task<IReadOnlyList<StudioNote>> NotesAsync(string owner)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("SELECT note_id, text, ref_doc, ref_copy, ref_page, created_at FROM studio_notes WHERE owner=$1 ORDER BY created_at DESC LIMIT 500", c);
        q.Parameters.AddWithValue(owner);
        var list = new List<StudioNote>();
        await using var r = await q.ExecuteReaderAsync();
        while (await r.ReadAsync())
            list.Add(new(r.GetString(0), r.GetString(1), r.IsDBNull(2) ? null : r.GetString(2), r.IsDBNull(3) ? null : r.GetString(3), r.IsDBNull(4) ? null : r.GetInt32(4), r.GetDateTime(5)));
        return list;
    }

    public async Task<bool> DeleteNoteAsync(string owner, string id)
    {
        await using var c = await db.OpenConnectionAsync();
        await using var q = new NpgsqlCommand("DELETE FROM studio_notes WHERE owner=$1 AND note_id=$2", c);
        q.Parameters.AddWithValue(owner); q.Parameters.AddWithValue(id);
        return await q.ExecuteNonQueryAsync() > 0;
    }
}

public sealed class StudioConflictException(int current) : Exception($"A newer version ({current}) was saved first.")
{
    public int Current { get; } = current;
}
