// C16 B06 test host. Commands:
//   <any activation CLI command>   with optional pause points from the environment:
//       MIMAMSA_ACTIVATION_PAUSE_AT=<step>    print "PAUSED <step>" and block forever at that step (the test kills it)
//       MIMAMSA_ACTIVATION_STEP_DELAY_MS=<n>  sleep n ms at every step (random-offset kills)
//   participant-host --site <dir> --pipe <name> [--key <file>] [--development]
//       a stand-in web process: ActivationParticipant + ControlChannelServer; prints READY, then answers stdin lines
//       ("status", "reload"); exits when stdin closes.
using Mimamsa.Core.Activation;

if (args.Length > 0 && args[0] == "participant-host")
{
    var a = new ActivationCli.Args(args);
    var site = new SiteLayout(a.Req("site"));
    var insp = new SiteInspector(site, ActivationCli.Reader(site, !a.Flag("development")));
    var p = new ActivationParticipant(insp);
    p.LoadHead();
    await using var server = new ControlChannelServer(new ControlChannelOptions
    {
        PipeName = a.Req("pipe"), Secret = ControlChannelOptions.LoadSecret(a["key"] ?? site.ChannelKeyPath),
    }, p) { Log = m => Console.Error.WriteLine(m) };
    server.Start();
    Console.WriteLine("READY");
    Console.Out.Flush();
    string? line;
    while ((line = Console.ReadLine()) is not null)
    {
        if (line == "status")
        {
            var serving = p.IsServing(out var why);
            Console.WriteLine($"{{\"serving\":{(serving ? "true" : "false")},\"reason\":\"{why}\",\"loaded\":\"{p.LoadedKnowledge}\",\"switching\":{(p.Switching ? "true" : "false")},\"rejected\":{server.Rejected}}}");
            Console.Out.Flush();
        }
        else if (line == "reload") { p.LoadHead(); Console.WriteLine("RELOADED"); Console.Out.Flush(); }
    }
    return 0;
}

var pauseAt = Environment.GetEnvironmentVariable("MIMAMSA_ACTIVATION_PAUSE_AT");
var continueFile = Environment.GetEnvironmentVariable("MIMAMSA_ACTIVATION_CONTINUE_FILE");
int delay = int.TryParse(Environment.GetEnvironmentVariable("MIMAMSA_ACTIVATION_STEP_DELAY_MS"), out var d) ? d : 0;
void Hook(string step)
{
    if (delay > 0) Thread.Sleep(delay);
    if (pauseAt is not null && step == pauseAt)
    {
        Console.WriteLine("PAUSED " + step);
        Console.Out.Flush();
        // With MIMAMSA_ACTIVATION_CONTINUE_FILE the step resumes once that file exists; otherwise it blocks until killed.
        while (continueFile is null || !File.Exists(continueFile)) Thread.Sleep(continueFile is null ? Timeout.Infinite : 20);
    }
}
return ActivationCli.Run(args, Console.Out, Hook, m => Console.Error.WriteLine(m));
