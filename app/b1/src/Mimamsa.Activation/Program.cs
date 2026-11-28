// C16 B06: activation tool entry point (interface IF-6). The single writer of the activation journal; see
// Mimamsa.Core/Activation/ActivationCli.cs for the commands. This production entry point registers no step hooks:
// crash and pause points exist only in the test host (tests/Mimamsa.Activation.TestHost).
using Mimamsa.Core.Activation;

return ActivationCli.Run(args, Console.Out, stepHook: null, log: m => Console.Error.WriteLine(m));
