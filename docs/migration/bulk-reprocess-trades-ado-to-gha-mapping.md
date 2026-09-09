# bulk-reprocess-trades — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline ID | 115 |
| ADO YAML | `adhoc/bulk-reprocess-trades.yml` |
| GHA workflow | `.github/workflows/bulk-reprocess-trades.yml` |
| Category | 6 — Ad-hoc, **active** (3 runs, all succeeded, last 2026-02-25; avg 325 min) |
| Templates | none — fully inline |
| Stack | Python 3.11 (`pandas`, `requests`, `pyarrow`) |
| Owner | **unknown** (risk R1 — see below) |
| Linked variable groups | `internal-network-credentials` (id 207) |
| ADO MCP verification | `azure-devops-mcp` server failed to start (`npx @azure-devops/mcp` exits during init); metadata taken from `docs/samples/ado-api-responses.json` and `docs/pipeline-inventory-report.md` instead |

## Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger: none` (manual queue only) | `on: workflow_dispatch` | Real runs are manual only, as in ADO. |
| — | `on: pull_request` (branches `main`, paths: this workflow file only) | **Intentional addition** (playbook rule): a *smoke pass* on `ubuntu-latest` that runs checkout → Python → `pip install` and **skips** the reprocess and artifact steps (`if: github.event_name == 'workflow_dispatch'`). It never touches internal systems or runs for hours; it only proves the workflow parses and its toolchain resolves when the file changes. |
| `parameters.startDate` (string, default `2024-01-01`) | `inputs.startDate` (string, required, same default) | Runtime parameter → dispatch input |
| `parameters.endDate` (string, default `2024-01-31`) | `inputs.endDate` (string, required, same default) | |
| `parameters.tradeTypes` (string, default `all`) | `inputs.tradeTypes` (string, required, same default) | |

ADO `${{ parameters.* }}` are compile-time template expansions substituted directly into the
script text. In GHA the inputs are passed through step `env:` (`START_DATE`, `END_DATE`,
`TRADE_TYPES`) and quoted in bash rather than interpolated into `run:` — same values, but
no shell-injection surface from free-text inputs.

## Stage / job mapping

The ADO pipeline has a single implicit stage with one job.

| ADO job | GHA job | `runs-on` | Timeout |
|---|---|---|---|
| `ReprocessTrades` — "Bulk reprocess trades" (`timeoutInMinutes: 480`) | `reprocess-trades` — "Bulk reprocess trades" | `[self-hosted, linux]` on `workflow_dispatch`; `ubuntu-latest` for the PR smoke pass | `timeout-minutes: 480` |

The ADO YAML is a bare `jobs:` list with no `stages:`; the GHA workflow likewise has one job.

### Step-by-step

| # | ADO step | GHA step | Notes |
|---|---|---|---|
| 0 | implicit `checkout: self` | `actions/checkout@v4` | |
| 0a | — (`$(Build.ArtifactStagingDirectory)` pre-exists on ADO agents) | `Create artifact staging directory` (`mkdir -p $RUNNER_TEMP/staging/reprocessed`, exports `BUILD_ARTIFACTSTAGINGDIRECTORY`) | Fresh runner: directory must be created explicitly |
| 1 | `UsePythonVersion@0` `versionSpec: '3.11'` | `actions/setup-python@v5` `python-version: 3.11` | |
| 2 | `script` "Install dependencies" — `pip install pandas requests pyarrow` | `run:` identical command | Unpinned versions preserved as-is (pre-existing) |
| 3 | `script` "Reprocess trades" (`timeoutInMinutes: 420`) — `python adhoc/scripts/reprocess_trades.py --start-date … --end-date … --types … --output $(Build.ArtifactStagingDirectory)/reprocessed/` | `run:` same command, `timeout-minutes: 420`, params via env, `if: github.event_name == 'workflow_dispatch'` | |
| 4 | `PublishBuildArtifacts@1` `pathToPublish: $(Build.ArtifactStagingDirectory)` `artifactName: reprocessed-trades` | `actions/upload-artifact@v4` `name: reprocessed-trades` `path: ${{ runner.temp }}/staging` `retention-days: 90`, `if: github.event_name == 'workflow_dispatch'` | Runs only on success, as in ADO (no `if: always()`) |

## Task mapping

| ADO task | GHA equivalent |
|---|---|
| `UsePythonVersion@0` | `actions/setup-python@v5` |
| `script` | `run:` |
| `PublishBuildArtifacts@1` | `actions/upload-artifact@v4` |

## Variable mapping

| ADO | GHA |
|---|---|
| `$(Build.ArtifactStagingDirectory)` | `$BUILD_ARTIFACTSTAGINGDIRECTORY` = `$RUNNER_TEMP/staging` (set via `$GITHUB_ENV`) |
| `$(Build.SourceBranch)` | `BUILD_SOURCEBRANCH: ${{ github.ref }}` |
| `$(Build.SourceVersion)` | `BUILD_SOURCEVERSION: ${{ github.sha }}` |
| `$(Build.BuildId)` | `BUILD_BUILDID: ${{ github.run_id }}` |
| `$(Build.SourcesDirectory)` | `BUILD_SOURCESDIRECTORY: ${{ github.workspace }}` |
| `$(Build.RequestedFor)` | `BUILD_REQUESTEDFOR: ${{ github.actor }}` |
| `$(Build.DefinitionName)` | `BUILD_DEFINITIONNAME: ${{ github.workflow }}` |
| ADO `_build/results?buildId=` URL | `PIPELINE_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` |
| variable group `internal-network-credentials` → `INTERNAL_SVC_ACCOUNT` (`svc-ci-runner@contoso-financial.com`) | `vars.INTERNAL_SVC_ACCOUNT` |
| variable group `internal-network-credentials` → `INTERNAL_SVC_PASSWORD` (secret) | `secrets.INTERNAL_SVC_PASSWORD` |
| variable group `internal-network-credentials` → `INTERNAL_CA_CERT_PATH` (`/etc/ssl/certs/contoso-internal-ca.pem`) | `vars.INTERNAL_CA_CERT_PATH`, falling back to the ADO value; the file must exist on the self-hosted runner |

The shims beyond `BUILD_ARTIFACTSTAGINGDIRECTORY` are not consumed by the inline YAML but are
provided so `adhoc/scripts/reprocess_trades.py` (which may read ADO env vars) behaves the same.

## Condition mapping

None — the ADO pipeline has no `condition:` expressions. All steps run sequentially and
stop on first failure, matching GHA defaults.

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| Artifactory registration | none | none |
| D2 / release-orchestrator notification | none | none |
| Compliance attestation | none | none |
| Test results | none | none |
| Build artifacts | `reprocessed-trades` (90-day retention rule, min 5 kept) | `reprocessed-trades` artifact, `retention-days: 90` (GHA has no "minimum to keep" equivalent) |

No `build-tools/scripts/` helper is called, so **no helper-script changes** were needed.

## Risk flags & how they are handled

| Flag | Handling |
|---|---|
| **R1 — no owner** (`owner_team: unknown`, last modified by `unknown-service-account@contoso.com`) | Not blocking. Flagged here and in `docs/ownership-gaps.md`. An owner must be found before the self-hosted runner and `INTERNAL_NETWORK_CREDENTIALS` secret can be provisioned, and to confirm the contents of variable group 207. |
| **R15 — 480 min timeout exceeds GHA hosted limit (360 min)**; avg run 325 min, longest observed 5 h 25 m | `runs-on: self-hosted` + `timeout-minutes: 480` (job) / `420` (step). Self-hosted runners have no 6 h cap (35-day max). **Alternative:** re-home as a batch job (K8s `Job`/`CronJob`, AWS Batch, or Azure Container Apps Job) triggered by a thin `workflow_dispatch` workflow that only submits the job and polls — keeps the manual UI while removing CI infra from the data-processing path. Recommended if a self-hosted runner pool with internal-network access does not already exist. |
| **R6 — internal-network credentials** | Variable group `internal-network-credentials` (id 207, per `docs/samples/ado-api-responses.json`) → `vars.INTERNAL_SVC_ACCOUNT`, `secrets.INTERNAL_SVC_PASSWORD`, `vars.INTERNAL_CA_CERT_PATH`, exposed to the reprocess step only, under the same env var names the ADO agent exported. The self-hosted runner must sit in the same network segment as the trade data sources and carry the internal CA cert at the configured path. |
| **R7 — little run history** (3 runs) | All 3 succeeded; last parameters used: `startDate=2026-01-01 endDate=2026-01-31 tradeTypes=fx-forwards`. Recommend the first GHA run replays that window and diffs against ADO build 96800's `reprocessed-trades` artifact. |

## Known gaps / behavioural differences

1. **`adhoc/scripts/reprocess_trades.py` does not exist in this repository.** The ADO YAML
   references it, but `adhoc/` contains only the two pipeline YAMLs. Either the script lives
   on the agent / a different repo, or the pipeline is currently broken. Preserved as-is
   (pre-existing); the workflow will fail at the "Reprocess trades" step until the script
   is added.
2. **Variable group linked implicitly.** The ADO definition links `internal-network-credentials`
   (id 207) at the definition level; the YAML never declares it under `variables:`. Whether
   `reprocess_trades.py` actually reads those env vars cannot be verified (see 1). All three
   are exported under their original names so behaviour is unchanged if it does.
3. **Runner.** ADO used the hosted `ubuntu-latest` image; real GHA runs require
   `[self-hosted, linux]`. Python 3.11 is installed via `actions/setup-python@v5`, which on
   self-hosted runners needs a writable tool cache (`AGENT_TOOLSDIRECTORY`/`RUNNER_TOOL_CACHE`).
4. **Artifact retention.** `retention-days: 90` matches ADO's `daysToKeep`; GHA has no
   equivalent of `minimumToKeep: 5`.
5. **Parameter interpolation.** ADO substituted parameters into the script text at compile time;
   GHA passes them as quoted env vars. Values containing spaces now reach the script as a single
   argument (ADO would have word-split them).
6. **`pull_request` smoke trigger.** Added per the playbook, but scoped to changes of the workflow
   file itself and limited to a toolchain smoke pass on `ubuntu-latest`; the reprocess and
   upload steps are gated on `workflow_dispatch`.
7. **Migration validator.** `validate_migration.py` reports FAIL for *Stage → Job Mapping*
   (the ADO YAML has no `stages:`, so it counts 0 stages against 1 GHA job) and for the
   *Artifact/Test Baseline* checks (no `validation/baselines/bulk-reprocess-trades/`). Neither
   can be fixed in the workflow: the pipeline has no stages to map and no CI test/artifact
   baseline exists for a one-off data job. Fabricating a baseline would be misleading.

## Secrets required

| Name | Kind | Purpose |
|---|---|---|
| `INTERNAL_SVC_PASSWORD` | secret | Service-account password from variable group 207 |
| `INTERNAL_SVC_ACCOUNT` | repository/environment variable | `svc-ci-runner@contoso-financial.com` (non-secret in ADO) |
| `INTERNAL_CA_CERT_PATH` | repository/environment variable (optional) | Defaults to `/etc/ssl/certs/contoso-internal-ca.pem` if unset |

## Runner requirements

- Labels: `self-hosted`, `linux` (`bash`, `python` tool cache writable)
- Internal CA certificate present at `INTERNAL_CA_CERT_PATH`
- Network access to the internal trade data sources used by `reprocess_trades.py`
- Enough disk under `$RUNNER_TEMP` for the reprocessed output
