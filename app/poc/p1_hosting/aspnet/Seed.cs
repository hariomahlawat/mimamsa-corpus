// Test/fixture seeding for the R2-N01 PoC: synthetic sessions (token hashes only), grants and vault copies.
using System.Text.Json;
using MimamsaPoc.Core;
using Npgsql;

namespace MimamsaPocApi;

public static class Seed
{
    public static async Task ApplyAsync(NpgsqlDataSource db, Vault vault, string path)
    {
        using var doc = JsonDocument.Parse(await File.ReadAllTextAsync(path));
        var root = doc.RootElement;
        await using var c = await db.OpenConnectionAsync();
        await using (var t = new NpgsqlCommand("TRUNCATE poc_sessions, poc_grants, vault_copies", c)) await t.ExecuteNonQueryAsync();
        foreach (var s in root.GetProperty("sessions").EnumerateArray())
        {
            await using var q = new NpgsqlCommand("INSERT INTO poc_sessions VALUES ($1,$2,$3,$4, now() + interval '1 day')", c);
            q.Parameters.AddWithValue(AuthStore.Hash(s.GetProperty("token").GetString()!));
            q.Parameters.AddWithValue(s.GetProperty("user").GetString()!);
            q.Parameters.AddWithValue(s.GetProperty("session").GetString()!);
            q.Parameters.AddWithValue(s.TryGetProperty("admin", out var a) && a.GetBoolean());
            await q.ExecuteNonQueryAsync();
        }
        foreach (var cp in root.GetProperty("copies").EnumerateArray())
        {
            var src = cp.GetProperty("source").GetString()!;
            var sha = cp.GetProperty("sha256").GetString()!;
            if (!vault.Import(src, sha)) throw new InvalidOperationException($"vault import failed: content hash != address for {src}");
            await using var q = new NpgsqlCommand("INSERT INTO vault_copies(doc_id, copy_sha256, length) VALUES ($1,$2,$3)", c);
            q.Parameters.AddWithValue(cp.GetProperty("doc_id").GetString()!); q.Parameters.AddWithValue(sha);
            q.Parameters.AddWithValue(new FileInfo(vault.PathFor(sha)).Length);
            await q.ExecuteNonQueryAsync();
        }
        foreach (var g in root.GetProperty("grants").EnumerateArray())
        {
            await using var q = new NpgsqlCommand("INSERT INTO poc_grants VALUES ($1,$2)", c);
            q.Parameters.AddWithValue(g.GetProperty("user").GetString()!); q.Parameters.AddWithValue(g.GetProperty("doc_id").GetString()!);
            await q.ExecuteNonQueryAsync();
        }
    }
}
