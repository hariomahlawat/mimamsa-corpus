// Synthetic oracle from Serving §10 (R2-N01), run against the real PostgreSQL ledger in an isolated database.
// Independent check: pool counters are re-read from the DB and compared with expected values computed here.
using System.Collections.Concurrent;
using System.Text.Json;
using Npgsql;

namespace MimamsaPoc.Core;

public static class LedgerOracle
{
    const long KiB = 1024;

    public static async Task<string> RunAsync(string connString)
    {
        var results = new List<object>();
        void Check(string name, bool pass, object detail) => results.Add(new { name, pass, detail });
        await using var db = NpgsqlDataSource.Create(connString);

        // --- 1. site remaining 64 KiB, two simultaneous 64 KiB contenders on different connections, 200 trials
        int bothWon = 0, oneWon = 0, noneWon = 0;
        for (int t = 0; t < 200; t++)
        {
            var L = await Fresh(db, siteCap: 64 * KiB, connCap: 1024 * KiB);
            var a = L.TryReserveAsync($"conn:o:a{t}", 64 * KiB, "s", "d", "x", 0, 64 * KiB);
            var b = L.TryReserveAsync($"conn:o:b{t}", 64 * KiB, "s", "d", "x", 0, 64 * KiB);
            var r = await Task.WhenAll(a, b);
            int won = r.Count(x => x is not null);
            if (won == 2) bothWon++; else if (won == 1) oneWon++; else noneWon++;
        }
        Check("two_simultaneous_64KiB_contenders_only_one_reserves", bothWon == 0 && oneWon == 200, new { trials = 200, oneWon, bothWon, noneWon });

        // --- 2. partial accept 16 KiB: 48 KiB returns, 16 KiB stays charged; a second 64 KiB cannot start
        {
            var L = await Fresh(db, 64 * KiB, 1024 * KiB);
            var r1 = (await L.TryReserveAsync("conn:o:p1", 64 * KiB, "s", "d", "x", 0, 64 * KiB))!;
            await L.SettleAsync(r1, Settlement.Accepted, 16 * KiB, "oracle partial");
            var site = await L.PoolAsync("site");
            var r2 = await L.TryReserveAsync("conn:o:p2", 64 * KiB, "s", "d", "x", 0, 64 * KiB);
            var r3 = await L.TryReserveAsync("conn:o:p3", 48 * KiB, "s", "d", "x", 0, 48 * KiB);
            Check("partial_accept_16KiB_charges_16_releases_48", site.charged == 16 * KiB && site.reserved == 0 && r2 is null && r3 is not null,
                  new { site.charged, site.reserved, second64Reserved = r2 is not null, then48Reserved = r3 is not null });
            // duplicate settlement must not release or charge again
            var before = await L.PoolAsync("site");
            bool second = await L.SettleAsync(r1, Settlement.ReleasedZeroTransfer, 0, "oracle duplicate");
            var after = await L.PoolAsync("site");
            Check("duplicate_settlement_is_noop", !second && before == after, new { before, after });
            // drain after termination evidence returns the 16 KiB
            int drained = await L.DrainConnectionAsync("conn:o:p1", "oracle: connection terminated");
            var s2 = await L.PoolAsync("site");
            Check("drain_after_termination_releases_charge", drained == 1 && s2.charged == 0 && s2.reserved == 48 * KiB, new { drained, s2.charged, s2.reserved });
        }

        // --- 3. ambiguous return: full 64 KiB stays charged until proof; timeouts/restarts do not release it
        {
            var L = await Fresh(db, 64 * KiB, 1024 * KiB);
            var r1 = (await L.TryReserveAsync("conn:o:u1", 64 * KiB, "s", "d", "x", 0, 64 * KiB))!;
            await L.SettleAsync(r1, Settlement.Uncertain, 16 * KiB, "oracle ambiguous");
            var site = await L.PoolAsync("site");
            var r2 = await L.TryReserveAsync("conn:o:u2", 1, "s", "d", "x", 0, 1);
            var L2 = new CreditLedger(db, new CreditConfig(64 * KiB, 1024 * KiB, 0));   // simulated restart (new instance)
            await L2.InitAsync(false);
            var afterRestart = await L2.PoolAsync("site");
            int early = await L2.ReconcilePriorInstancesAsync("oracle early attempt", TimeSpan.FromHours(1));
            Check("uncertain_retains_full_reservation_across_restart", site.charged == 64 * KiB && r2 is null && afterRestart.charged == 64 * KiB && early == 0,
                  new { chargedBefore = site.charged, oneByteReserved = r2 is not null, chargedAfterRestart = afterRestart.charged, reconciledTooEarly = early });
        }

        // --- 4. connection limit: same connection, cap 64 KiB, two simultaneous 64 KiB requests (site plentiful)
        {
            int both = 0, one = 0;
            for (int t = 0; t < 100; t++)
            {
                var L = await Fresh(db, 8192 * KiB, 64 * KiB);
                var r = await Task.WhenAll(L.TryReserveAsync("conn:o:same", 64 * KiB, "s", "d", "x", 0, 1),
                                           L.TryReserveAsync("conn:o:same", 64 * KiB, "s", "d", "x", 0, 1));
                int w = r.Count(x => x is not null); if (w == 2) both++; else if (w == 1) one++;
            }
            Check("connection_cap_two_contenders_only_one_reserves", both == 0 && one == 100, new { trials = 100, one, both });
        }

        // --- 5. stress: 64 workers x 150 random operations; independent invariant sampling
        {
            var L = await Fresh(db, 512 * KiB, 128 * KiB);
            var violations = new ConcurrentBag<string>();
            using var cts = new CancellationTokenSource();
            long samples = 0, maxOutstanding = 0;
            var sampler = Task.Run(async () =>
            {
                while (!cts.IsCancellationRequested)
                {
                    await using var c = await db.OpenConnectionAsync();
                    await using var q = new NpgsqlCommand("SELECT pool_id, cap, reserved, charged FROM credit_pools", c);
                    await using var rd = await q.ExecuteReaderAsync();
                    while (await rd.ReadAsync())
                    {
                        long o = rd.GetInt64(2) + rd.GetInt64(3);
                        if (o > rd.GetInt64(1) || rd.GetInt64(2) < 0 || rd.GetInt64(3) < 0) violations.Add(rd.GetString(0));
                        if (rd.GetString(0) == "site") maxOutstanding = Math.Max(maxOutstanding, o);
                    }
                    Interlocked.Increment(ref samples);
                }
            });
            long reserved = 0, denied = 0, dbErrors = 0;
            var errCodes = new ConcurrentDictionary<string, int>();
            var workers = Enumerable.Range(0, 64).Select(w => Task.Run(async () =>
            {
                var rnd = new Random(w);
                for (int i = 0; i < 150; i++)
                {
                    string conn = $"conn:o:s{w % 16}";
                    try
                    {
                        var r = await L.TryReserveAsync(conn, rnd.Next(1, 64) * KiB, "s", "d", "x", 0, 1);
                        if (r is null) { Interlocked.Increment(ref denied); continue; }
                        Interlocked.Increment(ref reserved);
                        var s = (Settlement)rnd.Next(0, 3);
                        await L.SettleAsync(r, s, rnd.Next(0, (int)r.Amount + 1), "stress");
                        if (rnd.Next(4) == 0) await L.SettleAsync(r, Settlement.ReleasedZeroTransfer, 0, "stress duplicate");
                        if (rnd.Next(3) == 0) await L.DrainConnectionAsync(conn, "stress termination");
                    }
                    catch (PostgresException pe) { Interlocked.Increment(ref dbErrors); errCodes.AddOrUpdate(pe.SqlState + ":" + pe.ConstraintName, 1, (_, v) => v + 1); }
                }
            })).ToArray();
            await Task.WhenAll(workers);
            cts.Cancel(); await sampler;
            for (int w = 0; w < 16; w++) await L.DrainConnectionAsync($"conn:o:s{w}", "stress final termination");
            var site = await L.PoolAsync("site");
            await using var c2 = await db.OpenConnectionAsync();
            await using var q2 = new NpgsqlCommand("SELECT count(*) FROM credit_reservations WHERE state IN ('RESERVED','ACCEPTED','UNCERTAIN')", c2);
            long open = (long)(await q2.ExecuteScalarAsync())!;
            Check("stress_no_overcommit_no_negative_and_balances_to_zero",
                  violations.IsEmpty && dbErrors == 0 && site.reserved == 0 && site.charged == 0 && open == 0,
                  new { reserved, denied, dbErrors, samples, maxSiteOutstanding = maxOutstanding, siteCap = 512 * KiB,
                        violations = violations.Count, finalReserved = site.reserved, finalCharged = site.charged, openReservations = open, errCodes });
        }
        return JsonSerializer.Serialize(new { oracle = "Serving §10 synthetic credit oracle", allPass = results.All(r => (bool)r.GetType().GetProperty("pass")!.GetValue(r)!), results },
                                        new JsonSerializerOptions { WriteIndented = true, IncludeFields = true });
    }

    static async Task<CreditLedger> Fresh(NpgsqlDataSource db, long siteCap, long connCap)
    {
        var L = new CreditLedger(db, new CreditConfig(siteCap, connCap, 0));
        await L.InitAsync(resetForTest: true);
        return L;
    }
}
