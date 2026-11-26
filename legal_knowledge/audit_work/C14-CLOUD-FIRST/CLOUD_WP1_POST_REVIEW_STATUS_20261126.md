# Cloud WP1 post-review status — 26 November 2026

## Observed changes
- PR #62 head f5a84a21d4db15c5953bd30f52c132a0748faf43 supersedes e77598731177774c7c5da0c66c79a2db093748ae. The latest commit removes live GitHub Actions execution and moves credentials to an isolated persistent Linux host, with signed deployment-specific one-use approvals.
- PR #63 head 645c88279883d9b934982a6422279369a19d7b6f supersedes the registration stub with an informational notice. Not needed for actual inventory; do not merge for activation.
- Verified actual final logs: dedicated synthetic job 139924693074, 9/9 passed including signed replay test; audit job 139924693611, 1135 total, 29 skipped, 1106 passed, zero failures. No live metadata job. Both PRs remain draft; formal independent review submission not visible in GitHub review list. Synthetic tests are not live commissioning or legal acceptance.

## Operating implication
Branch-name restriction and application-level commit pin alone are not an independent boundary against a repository writer who can alter the credential-consuming workflow. The latest code resolves this by removing the credentialed workflow rather than relaxing the boundary. No further GitHub environment variable or workflow dispatch is required. Owner should remove the now-unused environment secret HF_WP1_READ_TOKEN and revoke its dedicated HF token; do not expose the secret. This is account cleanup, not an allegation of compromise. The assistant connector cannot perform or verify those account actions.

The proposed isolated host is not provisioned or approved. It may entail cost and further owner operations; no new host, paid compute, or acquisition should be initiated implicitly. Continue public official source discovery and exact known-holding metadata checks through existing connected tools while evaluating existing suitable cloud execution capacity. Do not use the read/write sync credential, evade host checks, or reintroduce the removed live workflow. Preserve cloud-first and no routine workstation processing. Keep all prior acquisition/recovery/release holds.

## Source reconciliation increment (A4-ACQ-034)
India Code's consolidated Armed Forces Tribunal Act, 2007, last updated 29 September 2021, printed p.3, footnote 1 to s.1(2), explicitly labels the commencement notification S.O. 14(E), dated 13 June 2008, Gazette Extraordinary Part II, s.3(ii), with commencement on 15 June 2008.
Source: https://upload.indiacode.nic.in/showfile?actid=AC_CEN_28_38_00013_200755_1517807323574&filename=a2007-55.pdf&type=actfile
The Ministry of Defence PIB release of 24 July 2008 independently corroborates the effective date: https://www.pib.gov.in/newsite/erelcontent.aspx?lang=2&reg=48&relid=40606
India Code page-image retrieval timed out. Evidence is official-hosted consolidated text and contemporaneous official statement, not the original notification. Prior S.R.O. attribution remains a discrepancy; seek original Part II, s.3(ii) Gazette issue. No source bytes acquired, no HF writes, no legal promotion or request closure.
