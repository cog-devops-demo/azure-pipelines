# settlement-gateway-classic (classic / designer ADO definition)

`settlement-gateway-classic` is a **classic** Azure DevOps build definition: its steps live in
the ADO service as JSON, not in an `azure-pipelines.yml` in this repository. It exists so the
migration flow has to handle the non-YAML case — read the definition out of ADO, recover intent,
and emit a GitHub Actions workflow.

- Organization / project: `danagajewski` / `danagajewski-demo`
- Definition id: `9`
- Source: `GET https://dev.azure.com/danagajewski/danagajewski-demo/_apis/build/definitions/9?api-version=7.1`
- Agent pool: `Azure Pipelines` (hosted)
- Triggers: CI and PR validation on `main`, path-filtered to `/services/settlement-gateway`

## What it does

| Step | Task | Notes |
|------|------|-------|
| Use Python 3.11 | `UsePythonVersion@0` | |
| Stamp version and write build manifest | `PowerShell@2` (inline) | validates `SETTLEMENT_ENV`, derives a version from branch + build id, writes `build-manifest.json` with per-file hashes |
| Install dependencies | `Bash@3` | `pip install -r services/settlement-gateway/requirements.txt` |
| Run unit tests | `Bash@3` | pytest with JUnit XML output |
| Publish test results | `PublishTestResults@2` | run name `settlement gateway unit tests` |
| Package and register artifact | `PowerShell@2` (inline) | zips the package, records a registry receipt; warns and writes a local receipt when no registry URL is configured |
| Publish build artifact | `PublishBuildArtifacts@1` | artifact `settlement-gateway-drop` |

## Migration input

The validator needs the definition on disk, so an export is checked in at
`docs/migration/ado-exports/settlement-gateway-classic.json` (refresh it with the REST call above
after changing the definition). `validation/scripts/validate_migration.py` detects a `.json` ADO
source, flattens the phases and inline scripts, and scores the generated workflow against them
exactly as it does for YAML pipelines.

Runtime parity is unchanged: the classic definition and the migrated workflow both build the same
commit, and `validation/scripts/parity_report.py` compares build result, test counts and artifact
names from the live runs.
