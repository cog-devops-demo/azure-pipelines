# Validation baselines

Equivalence is decided by runtime parity: `validation/scripts/parity_report.py` reads the live
Azure DevOps run and the live GitHub Actions run of the *same commit* and compares result, test
count and artifacts. These files are the fallback for when no such pair of runs exists.

Each `<service>/expected-artifacts.json` and `<service>/test-counts.json` records what the
Azure DevOps pipeline for that service produced on one earlier run. They are advisory: the
scorecard prints them for context but they cannot pass or fail a migration on their own,
because a stored number goes stale the moment either pipeline changes.

Provenance fields:

- `status: observed` — captured from a real run (as opposed to `provisional`/`placeholder`,
  which the validator rejects).
- `source: azure-devops-run`
- `ado_build_id` / `ado_commit` — the ADO build and repository commit the numbers came from.
- `measurement` (test baselines) — where the count was read: an ADO test run, or the test
  runner summary in the build log for stacks that publish no test results to ADO
  (cargo, go test, node:test).

Services with no baseline directory have no ADO run to measure yet; the validator reports that
as an advisory EXCEPTION and the parity section reports the missing ADO run — neither is ever
reported as a pass.

To refresh a baseline, re-run the ADO pipeline and update the values plus `ado_build_id`,
`ado_commit`, and `last_updated`.
