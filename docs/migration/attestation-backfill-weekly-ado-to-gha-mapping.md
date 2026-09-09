# attestation-backfill-weekly — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `attestation-backfill-weekly` (ID **114**, path `\Night Jobs\Compliance`) |
| ADO YAML | `night-jobs/compliance/attestation-backfill.yml` |
| GHA workflow | `.github/workflows/attestation-backfill-weekly.yml` |
| Category | 5 — Non-build workload (small, owned) |
| Owner | shared-ci-platform |
| Templates consumed | none (fully inline); calls `build-tools/compliance/generate_metadata.py` |
| Stack | Python 3.11 (`requests`, `pandas`) |
| Risk flags | R14 self-hosted `linux-build-workers` (compliance-store network access); R10 365-day audit retention; avg runtime 93 min (last run 2026-03-16, 1 h 33 m) |

## Category 5 override

The migration playbook stops at Phase 1 for Category 5 (non-build) pipelines and
recommends dedicated compute instead of GHA. **For ADO 114 only, that rule is overridden**:
the inventory disposition (`docs/pipeline-inventory-report.md`) is *"Migrate to GHA — only
non-build job with a clear owner and a modest footprint (avg 93 min); runs fine on a
self-hosted GHA runner in the same network segment."*, and the requester confirmed the
override. Rationale:

- Single, short, well-understood job (four script steps + one artifact publish).
- Clear owner (shared-ci-platform), unlike the other night-jobs.
- Runtime (93 min avg, 180 min cap) is far below the 6 h GHA job limit and the job
  runs on a self-hosted runner anyway, so no hosted-runner constraints apply.
- Compliance-store access is satisfied by keeping the job on the same
  `linux-build-workers` network segment via a self-hosted runner label.

No other Category 5 pipeline is covered by this override.

## Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger: none` | no `push` trigger | This is a scheduled operational job, not CI. |
| — | `on.pull_request` (`branches: [main]`, paths: this workflow, `night-jobs/compliance/**`, `build-tools/compliance/**`) | Added as a **dry-run smoke test**: on `pull_request` the job runs on `ubuntu-latest`, `DRY_RUN=true` is passed to `backfill_attestations.py`, and the `Record backfill metadata` step (store upload) is skipped. A PR can never write to the attestation store. |
| `schedules[0].cron: '0 3 * * 0'`, `branches: [main]`, `always: true` | `on.schedule: [{cron: '0 3 * * 0'}]` gated by `vars.ATTESTATION_BACKFILL_GHA_CUTOVER == 'true'` | GHA scheduled workflows always run from the default branch (`main`) and always run regardless of changes, matching `always: true`. Both are UTC. The job-level `if:` keeps the GHA schedule **inert until cutover** (see below) so ADO 114 and GHA never both run the live backfill. |
| — | `on.workflow_dispatch` | Added so operators can trigger a manual re-run (ADO allowed manual queueing of any pipeline). |
| — | `concurrency: {group: attestation-backfill-weekly, cancel-in-progress: false}` | Prevents a manual dispatch from overlapping the weekly run and double-writing attestations. |

### Schedule cutover sequence (avoid duplicate weekly runs)

ADO definition 114 is **enabled** and scheduled for the same Sunday 03:00 UTC slot
(`docs/samples/ado-api-responses.json`). GHA `concurrency` cannot coordinate with ADO, so the
GHA job carries `if: github.event_name != 'schedule' || vars.ATTESTATION_BACKFILL_GHA_CUTOVER == 'true'`.
Until the repository variable exists and equals `true`, scheduled GHA runs are skipped;
`workflow_dispatch` and `pull_request` runs are unaffected.

1. Merge this PR. Scheduled GHA runs are skipped; ADO 114 keeps running.
2. Optionally validate with a `workflow_dispatch` run **outside** the Sunday 03:00 window
   (or after confirming the ADO run has finished — avg 93 min).
3. In one change window (any time other than Sunday 02:00–06:00 UTC):
   a. Disable the schedule on ADO definition 114 (or disable the definition).
   b. Create repository variable `ATTESTATION_BACKFILL_GHA_CUTOVER=true`.
4. Confirm the next Sunday run appears in GitHub Actions and not in ADO.
5. Rollback = delete the variable (GHA schedule goes inert again) and re-enable ADO 114.

## Job / stage mapping

| ADO | GHA |
|---|---|
| `jobs[0].job: BackfillAttestations` / `displayName: Backfill missing attestations` | `jobs.backfill-attestations` / `name: Backfill missing attestations` |
| `pool.name: linux-build-workers` + `demands: Agent.OS -equals Linux` | `runs-on: ${{ github.event_name == 'pull_request' && 'ubuntu-latest' \|\| 'linux-build-workers' }}` — self-hosted `linux-build-workers` label for schedule/dispatch (R14 store access), hosted `ubuntu-latest` for PR dry-runs |
| `timeoutInMinutes: 180` | `timeout-minutes: 180` |
| step `timeoutInMinutes: 120` (Regenerate attestations) | step `timeout-minutes: 120` |

## Step / task mapping

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 0 | implicit `checkout: self` | `actions/checkout@v4` | |
| 1 | `UsePythonVersion@0` (`versionSpec: '3.11'`) | `actions/setup-python@v5` (`python-version: '3.11'`) | Self-hosted runners need the `setup-python` tool cache or a system Python; see *Secrets & runner prerequisites*. |
| 2 | `script: pip install requests pandas` | `run: pip install requests pandas` | Unchanged. |
| — | `$(Build.ArtifactStagingDirectory)` created implicitly by the ADO agent | `Prepare staging directory`: `mkdir -p "$RUNNER_TEMP/staging"` and export `STAGING_DIR` via `$GITHUB_ENV` | GHA does not pre-create a staging dir; `runner` context is not available in job-level `env`, hence `$RUNNER_TEMP` + `GITHUB_ENV`. |
| 3 | `script` "Scan for attestation gaps" → `scan_attestation_gaps.py --output $(Build.ArtifactStagingDirectory)/gaps.json` | same command with `--output "$STAGING_DIR/gaps.json"` | |
| 4 | `script` "Regenerate attestations" → `backfill_attestations.py --gaps … --dry-run false` (`timeoutInMinutes: 120`) | same command with `--dry-run "$DRY_RUN"`, `timeout-minutes: 120` | `DRY_RUN` is `false` on `schedule`/`workflow_dispatch` (parity with ADO) and `true` on `pull_request`. |
| 5 | `script` "Record backfill metadata" → `python $(Build.SourcesDirectory)/build-tools/compliance/generate_metadata.py --build-id $(Build.BuildId) …` | `python "$GITHUB_WORKSPACE/build-tools/compliance/generate_metadata.py" --build-id "${{ github.run_id }}" …` with ADO env shims (below); `if: github.event_name != 'pull_request'` | Script unmodified. Skipped on PR dry-runs so no metadata is uploaded to the store. |
| 6 | `PublishBuildArtifacts@1` (`pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: attestation-backfill-report`, `condition: always()`) | `actions/upload-artifact@v4` (`name: attestation-backfill-report`, `path: ${{ runner.temp }}/staging`, `if: always()`, `retention-days: 365`, `if-no-files-found: warn`) | Retention set explicitly to satisfy R10 (ADO retention rule: 365 days / min 52 builds). |

## Variable / env-var mapping

`build-tools/compliance/generate_metadata.py` reads ADO agent variables via `os.environ`.
They are shimmed on the "Record backfill metadata" step so the script runs unmodified:

| ADO variable (env name read by script) | GHA value |
|---|---|
| `$(Build.DefinitionName)` → `BUILD_DEFINITIONNAME` | `${{ github.workflow }}` |
| `$(Build.Repository.Name)` → `BUILD_REPOSITORY_NAME` | `${{ github.event.repository.name }}` (repository name only, matching ADO's short name rather than `owner/repo`) |
| `$(Build.SourceBranch)` → `BUILD_SOURCEBRANCH` | `${{ github.ref }}` |
| `$(Build.SourceVersion)` → `BUILD_SOURCEVERSION` | `${{ github.sha }}` |
| `$(Agent.Name)` → `AGENT_NAME` | `${{ runner.name }}` |
| `$(Build.ArtifactStagingDirectory)` → `BUILD_ARTIFACTSTAGINGDIRECTORY` | `${{ runner.temp }}/staging` |
| `$(Build.BuildId)` (CLI arg `--build-id`) | `${{ github.run_id }}` |
| `$(Build.SourcesDirectory)` | `$GITHUB_WORKSPACE` |
| — | `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` (provided for forward compatibility; the script does not currently build a URL) |
| — | `DRY_RUN` = `'true'` on `pull_request`, else `'false'` |
| Variable group `compliance-store-credentials` (id 206): `COMPLIANCE_STORE_URL` (plain) | job env `COMPLIANCE_STORE_URL: https://compliance-store.contoso-financial.com/api/v2` (value from the ADO API snapshot) |
| group 206: `COMPLIANCE_STORE_TOKEN` (secret) | `${{ secrets.COMPLIANCE_STORE_TOKEN }}` |
| group 206: `COMPLIANCE_STORE_CERT_THUMBPRINT` (secret) | `${{ secrets.COMPLIANCE_STORE_CERT_THUMBPRINT }}` |

The three variable names/values come from the variable-group section of
`docs/samples/ado-api-responses.json` (group 206 is shared with pipeline 107). None of the
three scripts currently read them (the store call is stubbed), but they are exposed with the
same names so the scripts keep working unchanged when the attestation-database client is
wired up.

## Condition mapping

| ADO | GHA |
|---|---|
| `condition: always()` on `PublishBuildArtifacts@1` | `if: always()` on `upload-artifact` |
| (implicit: ADO schedule enabled) | job `if: github.event_name != 'schedule' \|\| vars.ATTESTATION_BACKFILL_GHA_CUTOVER == 'true'` (cutover gate, see above) |
| — | step `if: github.event_name != 'pull_request'` on `Record backfill metadata` |

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| attestation-database / compliance-store | reached from `linux-build-workers` self-hosted pool | same network segment via `runs-on: [self-hosted, linux-build-workers]` |
| Compliance metadata (`generate_metadata.py`) | writes `<artifact>-compliance-metadata.json` into staging dir, "uploads" to store | identical; env shims keep `pipeline`/`repository`/`branch`/`commit`/`agent` fields populated instead of `unknown` |
| Artifactory / release orchestrator / D2 notifications | not used by this pipeline | n/a |
| Artifact registration guard (`github.event_name == 'push'`) | n/a | n/a — the workflow has no `push` trigger and registers nothing in an artifact registry; the only artifact is the GHA-native run artifact |

## Known gaps / behavioural differences

1. **PR dry-run is new behaviour** — ADO never ran this job on PRs. The GHA `pull_request` run is a hosted-runner smoke test (`DRY_RUN=true`, no metadata upload); it does not exercise store connectivity.
2. **Schedule drift** — GHA `schedule` triggers can be delayed several minutes at the top of the hour under load and are disabled automatically after 60 days of repository inactivity. Neither affects ADO. Acceptable for a weekly compliance sweep; note it in the runbook.
3. **Python on self-hosted runners** — `actions/setup-python` on self-hosted runners requires the runner tool cache to be populated (or falls back to downloading). Ensure `linux-build-workers` runners have Python 3.11 available.
4. **Artifact retention ceiling** — `retention-days: 365` requires the repository/organization maximum artifact retention to be ≥ 365 days (org default is 90). If the org cap is lower, GHA silently clamps to the cap and R10 is not met — raise the org setting or ship the report to long-term storage.
5. **ADO `minimumToKeep: 52` retention rule** has no GHA equivalent; retention is time-based only.
6. **Concurrency** — ADO could run overlapping instances; the GHA workflow serialises them (`concurrency` group). This is a deliberate safety improvement, not parity. It does **not** coordinate with ADO — hence the cutover gate.
7. `if-no-files-found: warn` is added so a failed scan step still produces a (possibly empty) artifact upload without failing the `always()` publish step.
8. **`BUILD_REPOSITORY_NAME`** — ADO reported `shared-ci-platform`; GHA reports the GitHub repository name (`azure-pipelines`). Metadata consumers that key on repository name will see the new name from the first GHA run.

## Migration-validator scorecard (validate-migration)

`validation/scripts/validate_migration.py` was written for CI pipelines. Three checks cannot
pass for this pipeline without changing the validator, which is out of scope:

| Check | Result | Why |
|---|---|---|
| Stage → Job Mapping | FAIL `0/0 ADO stages mapped to GHA jobs` | The ADO YAML is jobs-only (no `stages:`), so the validator counts 0 ADO stages vs 1 GHA job. The single ADO job maps 1:1 to the single GHA job. |
| Artifact Baseline | FAIL `No artifact baseline found` | No `validation/baselines/attestation-backfill/expected-artifacts.json` exists. The validator rejects provisional/placeholder baselines, so one must be **measured from a real run** (expected: 2 `.json` files — `gaps.json`, `attestation-backfill-compliance-metadata.json`) and added by the owning team. |
| Test Baseline | FAIL `No test baseline found` | The pipeline has no test step in ADO or GHA; a test baseline is not applicable. |

## Secrets & runner prerequisites

| Item | Where | Purpose |
|---|---|---|
| `COMPLIANCE_STORE_TOKEN`, `COMPLIANCE_STORE_CERT_THUMBPRINT` | Repository / environment secrets | Secret members of the `compliance-store-credentials` variable group. |
| `ATTESTATION_BACKFILL_GHA_CUTOVER` | Repository variable (`vars`) | Set to `true` when the ADO schedule is disabled; enables scheduled GHA runs. |
| Self-hosted runner with label `linux-build-workers` | Org/repo runner group | R14 — network access to attestation-database. |
| Python 3.11 in the runner tool cache | Runner image | Required by `actions/setup-python@v5` on self-hosted runners. |
| Artifact retention limit ≥ 365 days | Org / repo settings | R10 audit retention. |

## Helper-script changes

None. `build-tools/compliance/generate_metadata.py` reads only ADO env vars that are fully
shimmed by the workflow and does not construct ADO-format URLs, so it needs no
GHA-compatibility changes. The two job scripts under `night-jobs/compliance/scripts/`
are argument-driven and unchanged.

## Verification performed

- `actionlint` passes on the new workflow.
- The four script steps were executed locally in sequence with the same arguments and env
  shims; `gaps.json` and `attestation-backfill-compliance-metadata.json` were produced in
  the staging directory as expected.
- ADO MCP verification was attempted but the configured `azure-devops-mcp` server points
  at a different org and fails to start; pipeline metadata (schedule, pool, variable group
  206, retention 365/52, latest run) was taken from `docs/samples/ado-api-responses.json`.
