using System.Diagnostics;

namespace Mimamsa.Tests;

/// Regression (local Windows commissioning): the harness passed the service DLL as one unquoted argument string, so a
/// checkout under "E:\Dot Net Web Development\..." made the host run "dotnet-E:\Dot" and 23 tests failed.
public class ServiceLaunchPathTests
{
    [Fact]
    public async Task ServiceDllPathWithSpacesReachesTheHostAsOneArgument()
    {
        var dir = Path.Combine(Path.GetTempPath(), "mimamsa path with spaces " + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        try
        {
            var dll = Path.Combine(dir, "Missing Service.dll");   // never created: the host must name it in full
            var psi = ServiceFixture.ServiceStartInfo(dll, dir);
            Assert.Equal(new[] { dll }, psi.ArgumentList);

            using var p = Process.Start(psi)!;
            var output = await p.StandardOutput.ReadToEndAsync() + await p.StandardError.ReadToEndAsync();
            Assert.True(p.WaitForExit(30_000));
            Assert.NotEqual(0, p.ExitCode);
            // The host echoes the path it received; split at a space it would stop at "...\mimamsa".
            Assert.Contains(dll, output);
        }
        finally { Directory.Delete(dir, true); }
    }
}
