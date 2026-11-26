# B1 local Windows commissioning: fixes for independent review

- **Base:** Cycle 13 staging `c1e4d461`. Local branch `claude/local-commission-c13`. Not pushed or merged.
- **Scope:** commissioning defects only. No features, no architecture changes, no Authority Ledger or approval-state changes.

## C1. Test harness split the service path at spaces

| Item | Detail |
| --- | --- |
| Symptom | Checked out under `E:\Dot Net Web Development\…`, 23 of 88 C# tests failed. The cause was `dotnet-E:\Dot does not exist`. |
| Cause | `ServiceFixture` passed the DLL path as a single unquoted argument string (`HttpTests.cs`, two call sites). |
| Fix | One `ServiceFixture.ServiceStartInfo(dll, workingDirectory)` builds the start info. It passes the path through `ProcessStartInfo.ArgumentList`, which quotes it. Both call sites use it. |
| Regression test | `ServiceLaunchPathTests.ServiceDllPathWithSpacesReachesTheHostAsOneArgument`. It starts the host with a missing DLL in a directory whose name contains spaces, then asserts that the host echoes the full path. With the old code the path would be cut at the first space. |
| Evidence | 89/89 C# tests pass when run from the spaced path. |
| Other launchers | `b1server.py` already passes an argument list, so it was not affected. |

## C2. The hash-pinned restricted-material register changed bytes on Windows checkout

| Item | Detail |
| --- | --- |
| Symptom | Checked out with `core.autocrlf=true`, `config/restricted_material.json` had SHA-256 `6efe7c8c…`. The 290-document sample release pins `fc7ea07e…` (`SAMPLE_MANIFEST.json` → `restricted_material.config_sha256`). |
| Consequence | Under fail-closed F16, a release built on Linux would refuse to start against the Windows checkout of its own register. Locally built releases would also pin a CRLF-only hash. |
| Fix | A new `.gitattributes` with `config/restricted_material.json -text`. The checked-out bytes now equal the blob on every platform: SHA-256 `fc7ea07e…`, the same as the pin. |
| Not changed | The register content and the F16 check itself. |
| Open question for the reviewer | Should other byte-pinned inputs get the same treatment? The SYN fixture passed either way. |
