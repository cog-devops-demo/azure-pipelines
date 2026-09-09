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
| `trigger: none` | (no `push` / `pull_request`) | Intentional: this is a scheduled operational job, not CI. The playbook's "add `on.pull_request`" rule is not applied — a PR must never run a live (non-dry-run) backfill against the attestation store. |
| `schedules[0].cron: '0 3 * * 0'`, `branches: [main]`, `always: true` | `on.schedule: [{cron: '0 3 * * 0'}]` | GHA scheduled workflows always run from the default branch (`main`) and always run regardless of changes, matching `always: true`. Both are UTC. |
| — | `on.workflow_dispatch` | Added so operators can trigger a manual re-run (ADO allowed manual queueing of any pipeline). |
| — | `concurrency: {group: attestation-backfill-weekly, cancel-in-progress: false}` | Prevents a manual dispatch from overlapping the weekly run and double-writing attestations. |

## Job / stage mapping

| ADO | GHA |
|---|---|
| `jobs[0].job: BackfillAttestations` / `displayName: Backfill missing attestations` | `jobs.backfill-attestations` / `name: Backfill missing attestations` |
| `pool.name: linux-build-workers` + `demands: Agent.OS -equals Linux` | `runs-on: [self-hosted, linux-build-workers]` |
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
| 4 | `script` "Regenerate attestations" → `backfill_attestations.py --gaps … --dry-run false` (`timeoutInMinutes: 120`) | same command, `timeout-minutes: 120` | Still `--dry-run false`; only ever runs on `schedule` / `workflow_dispatch`. |
| 5 | `script` "Record backfill metadata" → `python $(Build.SourcesDirectory)/build-tools/compliance/generate_metadata.py --build-id $(Build.BuildId) …` | `python "$GITHUB_WORKSPACE/build-tools/compliance/generate_metadata.py" --build-id "${{ github.run_id }}" …` with ADO env shims (below) | Script unmodified. |
| 6 | `PublishBuildArtifacts@1` (`pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: attestation-backfill-report`, `condition: always()`) | `actions/upload-artifact@v4` (`name: attestation-backfill-report`, `path: ${{ runner.temp }}/staging`, `if: always()`, `retention-days: 365`, `if-no-files-found: warn`) | Retention set explicitly to satisfy R10 (ADO retention rule: 365 days / min 52 builds). |

## Variable / env-var mapping

`build-tools/compliance/generate_metadata.py` reads ADO agent variables via `os.environ`.
They are shimmed on the "Record backfill metadata" step so the script runs unmodified:

| ADO variable (env name read by script) | GHA value |
|---|---|
| `$(Build.DefinitionName)` → `BUILD_DEFINITIONNAME` | `${{ github.workflow }}` |
| `$(Build.Repository.Name)` → `BUILD_REPOSITORY_NAME` | `${{ github.repository }}` |
| `$(Build.SourceBranch)` → `BUILD_SOURCEBRANCH` | `${{ github.ref }}` |
| `$(Build.SourceVersion)` → `BUILD_SOURCEVERSION` | `${{ github.sha }}` |
| `$(Agent.Name)` → `AGENT_NAME` | `${{ runner.name }}` |
| `$(Build.ArtifactStagingDirectory)` → `BUILD_ARTIFACTSTAGINGDIRECTORY` | `${{ runner.temp }}/staging` |
| `$(Build.BuildId)` (CLI arg `--build-id`) | `${{ github.run_id }}` |
| `$(Build.SourcesDirectory)` | `$GITHUB_WORKSPACE` |
| — | `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` (provided for forward compatibility; the script does not currently build a URL) |
| Variable group `compliance-store-credentials` (id 206) | `COMPLIANCE_STORE_TOKEN: ${{ secrets.COMPLIANCE_STORE_TOKEN }}` (job-level env) |

Note on the variable group: the ADO API snapshot (`docs/samples/ado-api-responses.json`)
links variable group 206 to this pipeline but does not expose the variable names inside it,
and none of the three scripts currently read any credential from the environment (they
stub the store call). The GHA workflow therefore exposes a single placeholder secret,
`COMPLIANCE_STORE_TOKEN`; rename/extend it to the real variable names when the
attestation-database client is wired up.

## Condition mapping

| ADO | GHA |
|---|---|
| `condition: always()` on `PublishBuildArtifacts@1` | `if: always()` on `upload-artifact` |
| (no other conditions) | — |

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| attestation-database / compliance-store | reached from `linux-build-workers` self-hosted pool | same network segment via `runs-on: [self-hosted, linux-build-workers]` |
| Compliance metadata (`generate_metadata.py`) | writes `<artifact>-compliance-metadata.json` into staging dir, "uploads" to store | identical; env shims keep `pipeline`/`repository`/`branch`/`commit`/`agent` fields populated instead of `unknown` |
| Artifactory / release orchestrator / D2 notifications | not used by this pipeline | n/a |
| Artifact registration guard (`github.event_name == 'push'`) | n/a | n/a — the workflow has no `push` trigger and registers nothing in an artifact registry; the only artifact is the GHA-native run artifact |

## Known gaps / behavioural differences

1. **Not a CI pipeline** — no `push`/`pull_request` triggers were added (intentional, see Trigger mapping). Validation of the workflow file therefore relies on `actionlint`, not on a PR run of the job itself.
2. **Schedule drift** — GHA `schedule` triggers can be delayed several minutes at the top of the hour under load and are disabled automatically after 60 days of repository inactivity. Neither affects ADO. Acceptable for a weekly compliance sweep; note it in the runbook.
3. **Python on self-hosted runners** — `actions/setup-python` on self-hosted runners requires the runner tool cache to be populated (or falls back to downloading). Ensure `linux-build-workers` runners have Python 3.11 available.
4. **Artifact retention ceiling** — `retention-days: 365` requires the repository/organization maximum artifact retention to be ≥ 365 days (org default is 90). If the org cap is lower, GHA silently clamps to the cap and R10 is not met — raise the org setting or ship the report to long-term storage.
5. **ADO `minimumToKeep: 52` retention rule** has no GHA equivalent; retention is time-based only.
6. **Concurrency** — ADO could run overlapping instances; the GHA workflow serialises them (`concurrency` group). This is a deliberate safety improvement, not parity.
7. `if-no-files-found: warn` is added so a failed scan step still produces a (possibly empty) artifact upload without failing the `always()` publish step.

## Secrets & runner prerequisites

| Item | Where | Purpose |
|---|---|---|
| `COMPLIANCE_STORE_TOKEN` | Repository / environment secret | Placeholder for the `compliance-store-credentials` variable group (see note above). |
| Self-hosted runner with labels `self-hosted`, `linux-build-workers` | Org/repo runner group | R14 — network access to attestation-database. `.github/actionlint.yaml` declares the custom label so `actionlint` passes. |
| Python 3.11 in the runner tool cache | Runner image | Required by `actions/setup-python@v5` on self-hosted runners. |
| Artifact retention limit ≥ 365 days | Org / repo settings | R10 audit retention. |

## Helper-script changes

None. `build-tools/compliance/generate_metadata.py` reads only ADO env vars that are fully
shimmed by the workflow and does not construct ADO-format URLs, so it needs no
GHA-compatibility changes. The two job scripts under `night-jobs/compliance/scripts/`
are argument-driven and unchanged.

## Verification performed

- `actionlint` passes on the new workflow (with `.github/actionlint.yaml` runner label).
- The four script steps were executed locally in sequence with the same arguments and env
  shims; `gaps.json` and `attestation-backfill-compliance-metadata.json` were produced in
  the staging directory as expected.
- ADO MCP verification was attempted but the configured `azure-devops-mcp` server points
  at a different org and fails to start; pipeline metadata (schedule, pool, variable group
  206, retention 365/52, latest run) was taken from `docs/samples/ado-api-responses.json`.
