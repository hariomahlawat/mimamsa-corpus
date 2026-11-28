// C16 B06: activation tool entry point (interface IF-6). The single writer of the activation journal; see
// Mimamsa.Core/Activation/ActivationCli.cs for the commands. This production entry point registers no step hooks:
// crash and pause points exist only in the test host (tests/Mimamsa.Activation.TestHost).
// C16 S3-C (B07/B08): installer, `stage`, backup and restore commands (Mimamsa.Core/Install/InstallCli.cs), and
// `service-job` (run one bounded job as a Windows service under its virtual account; installer acceptance tests).
using Mimamsa.Core.Activation;
using Mimamsa.Core.Install;

if (args.Length > 0 && args[0] == "service-job") return ServiceJob.Main(args);
if (args.Length > 0 && InstallCli.Commands.Contains(args[0])) return InstallCli.Run(args, Console.Out, m => Console.Error.WriteLine(m));
return ActivationCli.Run(args, Console.Out, stepHook: null, log: m => Console.Error.WriteLine(m));
