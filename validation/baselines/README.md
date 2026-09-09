# Validation baselines

Each `<service>/expected-artifacts.json` and `<service>/test-counts.json` records what the
Azure DevOps pipeline for that service actually produced, so the GitHub Actions workflow can be
compared against measured ADO behaviour instead of hand-written expectations.

Provenance fields:

- `status: observed` — captured from a real run (as opposed to `provisional`/`placeholder`,
  which the validator rejects).
- `source: azure-devops-run`
- `ado_build_id` / `ado_commit` — the ADO build and repository commit the numbers came from.
- `measurement` (test baselines) — where the count was read: an ADO test run, or the test
  runner summary in the build log for stacks that publish no test results to ADO
  (cargo, go test, node:test).

Services with no baseline directory have no ADO run to measure yet; the validator reports that
as a FAIL rather than assuming parity.

To refresh a baseline, re-run the ADO pipeline and update the values plus `ado_build_id`,
`ado_commit`, and `last_updated`.
