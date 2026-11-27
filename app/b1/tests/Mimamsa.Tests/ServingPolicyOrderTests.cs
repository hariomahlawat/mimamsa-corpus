using Mimamsa.Core.Delivery;

namespace Mimamsa.Tests;

/// Codex review of PR #70: a reinstatement whose durable commit is slow must not clear the fence of a withdrawal that
/// was requested while it was running, nor roll the epoch back. Policy operations are serialised end to end.
public class ServingPolicyOrderTests
{
    [Fact]
    public async Task ADelayedReinstatementCannotUndoALaterWithdrawal()
    {
        const string doc = "doc-a";
        var shas = new[] { new string('a', 64) };
        var st = new ServingState();
        st.Load(Array.Empty<(string, string)>(), 0, "d0");
        await st.WithdrawAsync(doc, shas, () => Task.FromResult((1L, "d1", true)), () => { }, (_, _) => { });
        Assert.True(st.IsDocWithdrawn(doc));

        // reinstatement: its durable commit (epoch 2) is held back
        var reinstateCommit = new TaskCompletionSource<(long, string, bool, List<string>)>(TaskCreationOptions.RunContinuationsAsynchronously);
        var reinstate = st.ReinstateAsync(doc, () => reinstateCommit.Task);

        // a second withdrawal (epoch 3) is requested while the reinstatement is in flight
        bool secondCommitRan = false;
        var withdraw = Task.Run(() => st.WithdrawAsync(doc, shas, () => { secondCommitRan = true; return Task.FromResult((3L, "d3", true)); }, () => { }, (_, _) => { }));
        await Task.Delay(200);
        Assert.False(secondCommitRan);                       // serialised: it waits for the reinstatement to finish

        reinstateCommit.SetResult((2L, "d2", true, shas.ToList()));
        await reinstate;
        await withdraw;

        Assert.True(secondCommitRan);
        Assert.True(st.IsDocWithdrawn(doc));                 // the later withdrawal stands
        Assert.True(st.IsWithdrawn(doc, shas[0]));
        Assert.Equal(3, st.Epoch);                           // never rolled back to 2
    }

    [Fact]
    public async Task TheMirrorNeverMovesTheEpochBackwards()
    {
        var shas = new[] { new string('b', 64) };
        var st = new ServingState();
        st.Load(Array.Empty<(string, string)>(), 5, "d5");
        await st.WithdrawAsync("doc-b", shas, () => Task.FromResult((4L, "d4", true)), () => { }, (_, _) => { });
        Assert.Equal(5, st.Epoch);
        Assert.True(st.IsDocWithdrawn("doc-b"));             // the fence itself is still applied
    }
}
