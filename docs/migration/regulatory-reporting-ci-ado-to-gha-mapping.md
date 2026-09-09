# regulatory-reporting-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `regulatory-reporting-ci` (ID **107**) |
| ADO YAML | `services/regulatory-reporting/azure-pipelines.yml` |
| GHA workflow | `.github/workflows/regulatory-reporting-ci.yml` |
| Category | 3 — Hybrid (team-override template + large inline compliance block) |
| Template branch | `team/reporting-hotfix` (see *Template source* below) |
| Stack | Python 3.11 |
| Owner | team-reporting |
| Pool | `ubuntu-latest` (hosted) → `runs-on: ubuntu-latest` |
| Avg runtime (ADO) | 82 min, 65 runs, 61 succeeded |
| Risk flags | R2, R5, R9, R10 |

## Template source

The pipeline consumes `alt-templates/team-overrides/team-build-custom.yml@templates` with
`resources.repositories.templates.ref: team/reporting-hotfix`.

**The `team/reporting-hotfix` branch does not exist in `cog-devops-demo/azure-pipelines`** (only `main`
and `devin/*` branches are present; `git show team/reporting-hotfix:...` fails). The Azure DevOps MCP
server could not be reached either (process exits on startup, and it is configured for a different org),
so the ADO-side branch could not be read. The template was therefore inlined **from `main`**.

`docs/branch-usage-notes.md` describes the hotfix branch as "added extra compliance metadata
generation steps" (audit-trail logging / pre-build validation). Those hotfix-only steps are **not**
in this workflow because their contents could not be read — see *Known gaps*. The `main` version of
the template was expanded with these parameter values:

| Parameter | Value | Effect |
|---|---|---|
| `language` | `python` | `UsePythonVersion@0` 3.11 + `pip install -r requirements.txt && pytest tests/ -v && python setup.py sdist bdist_wheel` |
| `complianceLevel` | `elevated` (from `$(complianceLevel)`) | passed to `generate_metadata.py` |
| `generateMetadata` | `true` (default) | `generate_metadata.py` step included |
| `artifactName` | `regulatory-compliance-pkg` | metadata artifact name + published artifact name |

## Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger.branches.include: [main]` | `on.push.branches: [main]` | |
| `trigger.paths.include: services/regulatory-reporting/**` | `on.push.paths` + `.github/workflows/regulatory-reporting-ci.yml` | workflow file added to path filter so workflow edits self-test |
| — (no PR trigger) | `on.pull_request` (main, same paths) | **intentional addition** for earlier feedback; the reports job is skipped on PRs (see below) |
| `schedules: cron '0 6 * * 1-5'`, `branches: main`, `always: true` | `on.schedule: cron '0 6 * * 1-5'` | GHA cron is UTC and always runs on the default branch (`main`), matching `always: true` |

## Stage → job mapping

| ADO stage / job | GHA job | `needs` | `if` | Environment | Timeout |
|---|---|---|---|---|---|
| `ComplianceBuild` / `build` (template) | `compliance_build` — "Build compliance package" | — | — | — | 60 min (ADO default) |
| `GenerateReports` / `reports` (`dependsOn: ComplianceBuild`, `timeoutInMinutes: 90`) | `generate_reports` — "Generate regulatory reports" | `compliance_build` | `push \|\| schedule` | `prod` + `concurrency: regulatory-reporting-prod` | 90 min |

### `compliance_build` steps (from `team-build-custom.yml`)

| # | ADO step | GHA step |
|---|---|---|
| 0 | (implicit checkout) | `actions/checkout@v4` |
| 1 | `script` "Log compliance context" | `run` echo with `$COMPLIANCE_LEVEL` / `python` |
| 2 | `UsePythonVersion@0` `versionSpec: 3.11` | `actions/setup-python@v5` `python-version: '3.11'` |
| 3 | `script` "Build and test (Python)" | identical commands, `working-directory: services/regulatory-reporting` (**intentional change** — the ADO template runs from the checkout root; the sources live in the service directory) |
| 4 | `script` "Generate compliance metadata" (`generateMetadata == true`) | `run` `build-tools/compliance/generate_metadata.py --artifact regulatory-compliance-pkg --compliance-level elevated --build-id $BUILD_BUILDID --store attestation-database`; guarded `if: push \|\| schedule`; `mkdir -p` staging first |
| 5 | `PublishBuildArtifacts@1` `pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: regulatory-compliance-pkg` | `actions/upload-artifact@v4` `name: regulatory-compliance-pkg`, `retention-days: 365`, `if-no-files-found: warn` |

### `generate_reports` steps (inline)

| # | ADO step | GHA step |
|---|---|---|
| 0 | (implicit checkout) | `actions/checkout@v4` |
| 1 | `UsePythonVersion@0` 3.11 | `actions/setup-python@v5` |
| 2 | `script` "Install dependencies" | `pip install -r services/regulatory-reporting/requirements.txt` |
| — | (ADO agent pre-creates `$(Build.ArtifactStagingDirectory)`) | "Prepare staging directory and build number": `mkdir -p .../staging/reports`; exports `BUILD_BUILDNUMBER` (fresh runner) |
| 3 | `script` "Generate regulatory reports" | same command; `--date "$BUILD_BUILDNUMBER"` |
| 4 | `script` "Upload compliance metadata" | `generate_metadata.py --artifact regulatory-reports ...` |
| 5 | `script` "Generate attestation record" | `generate_attestation.py --artifact regulatory-reports --env prod --build-id $BUILD_BUILDID` |
| 6 | `PublishBuildArtifacts@1` `pathToPublish: .../reports`, `artifactName: regulatory-reports` | `actions/upload-artifact@v4` `name: regulatory-reports`, `path: .../staging/reports`, `retention-days: 365`, `if-no-files-found: error` |

## Task mapping

| ADO task | GHA | Notes |
|---|---|---|
| `UsePythonVersion@0` (3.11) | `actions/setup-python@v5` | |
| `script` | `run:` (bash) | `defaults.run.shell: bash` |
| `PublishBuildArtifacts@1` | `actions/upload-artifact@v4` | `retention-days: 365` (R10) |
| `deployment`/environment checks (ADO `prod` env, configured in ADO UI) | `environment: prod` + `concurrency` | see *prod gate* |

## Variable mapping

| ADO | GHA | Scope |
|---|---|---|
| `complianceLevel: elevated` | `env.COMPLIANCE_LEVEL` | workflow |
| `$(Build.ArtifactStagingDirectory)` | `env.BUILD_ARTIFACTSTAGINGDIRECTORY = ${{ github.workspace }}/staging` | workflow (`runner.temp` is not available in workflow-level `env`) |
| `$(Build.BuildId)` | `env.BUILD_BUILDID = ${{ github.run_id }}` | workflow |
| `$(Build.BuildNumber)` (`yyyyMMdd.r`) | `BUILD_BUILDNUMBER = $(date -u +%Y%m%d).${{ github.run_number }}` | step → `$GITHUB_ENV` |
| `$(Build.SourcesDirectory)` | `env.BUILD_SOURCESDIRECTORY = ${{ github.workspace }}` | workflow |
| `$(Build.SourceBranch)` | `env.BUILD_SOURCEBRANCH = ${{ github.ref }}` | read by `generate_attestation.py`, `generate_metadata.py` |
| `$(Build.SourceVersion)` | `env.BUILD_SOURCEVERSION = ${{ github.sha }}` | idem |
| `$(Build.DefinitionName)` | `env.BUILD_DEFINITIONNAME = ${{ github.workflow }}` | idem |
| `$(Build.Repository.Name)` | `env.BUILD_REPOSITORY_NAME = ${{ github.repository }}` | `generate_metadata.py` |
| `$(Agent.Name)` / `$(Agent.OS)` | step-level `AGENT_NAME = ${{ runner.name }}`, `AGENT_OS = ${{ runner.os }}` | `runner.*` is only valid at step level |
| ADO pipeline URL | `env.PIPELINE_URL = <server>/<repo>/actions/runs/<run_id>` | not consumed by these scripts; provided for consistency with other migrations |
| VG 201 `shared-ci-secrets` → `PIP_INDEX_URL` | `vars.PIP_INDEX_URL` | only pip-relevant member is mapped |
| VG 206 `compliance-store-credentials` | `vars.COMPLIANCE_STORE_URL`, `secrets.COMPLIANCE_STORE_TOKEN`, `secrets.COMPLIANCE_STORE_CERT_THUMBPRINT` | step/job `env` |
| VG 209 `regulatory-reporting-config` | `secrets.REPORTING_DB_CONNECTION_STRING`, `vars.REPORTING_SMTP_SERVER`, `vars.REPORTING_DISTRIBUTION_LIST` | `generate_reports` job `env` |

## Condition mapping

| ADO | GHA | Notes |
|---|---|---|
| `${{ if eq(parameters.language, 'python') }}` | resolved at migration time → python steps inlined | .NET branch dropped |
| `${{ if eq(parameters.generateMetadata, true) }}` | resolved → step included | |
| `dependsOn: ComplianceBuild` (implicit `succeeded()`) | `needs: compliance_build` | |
| — (no condition on stages) | `generate_reports.if: github.event_name == 'push' \|\| github.event_name == 'schedule'` | **added**: PR runs would otherwise hit the `prod` approval gate and write to attestation-database |
| — | "Generate compliance metadata" step `if: push \|\| schedule` | registry-write guard (PR builds never register compliance records) |

## prod gate (R5)

ADO environment `prod` checks (from `docs/samples/ado-api-responses.json`):

| ADO check | GHA | Status |
|---|---|---|
| Approval — `release-managers` + `service-owner`, `minApprovers: 2` | GitHub environment `prod` → *Required reviewers* (add both teams; GHA requires **all** listed reviewers only if configured so — set 2 reviewers and enable "prevent self-review") | **manual repo setting** |
| Business hours — Mon–Thu 09:00–16:00 ET | none | **known gap** — GHA has no business-hours check; options: a *wait timer*, a custom deployment-protection-rule app, or a scheduled approver process |
| Exclusive lock | `concurrency: { group: regulatory-reporting-prod, cancel-in-progress: false }` | queued, one run at a time |

> Note: the ADO YAML itself does not declare `environment: prod`; the inventory (R5) and the `--env prod` attestation
> mark this pipeline as prod-gated. The gate is applied to the `generate_reports` job because that is the job that
> uploads to attestation-database and emits the prod attestation.

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| attestation-database (compliance metadata) | `generate_metadata.py`, both stages | same script, unmodified; push/schedule only |
| Compliance attestation | `generate_attestation.py --env prod` | same script, unmodified; env shims provide `BUILD_*`/`AGENT_OS` |
| Artifactory / `publish_artifact.py` | not used | n/a |
| D2 / release-orchestrator notification | not used | n/a |
| Test results | `pytest tests/ -v` (no `PublishTestResults@2` in ADO) | same; no results upload (none in ADO) |

## Retention (R10)

Both `upload-artifact` steps use `retention-days: 365`. GitHub caps this at the repository/organisation
*artifact and log retention* setting (default 90 days, max 400 for private repos). **The repo or org setting must
be raised to ≥ 365 days** or the value is silently clamped — verify in *Settings → Actions → General*.

## Helper scripts

No changes were required in `build-tools/`:

- `build-tools/compliance/generate_metadata.py` reads `BUILD_DEFINITIONNAME`, `BUILD_REPOSITORY_NAME`,
  `BUILD_SOURCEBRANCH`, `BUILD_SOURCEVERSION`, `AGENT_NAME`, `BUILD_ARTIFACTSTAGINGDIRECTORY` — all shimmed.
- `build-tools/scripts/generate_attestation.py` reads `BUILD_SOURCEBRANCH`, `BUILD_SOURCEVERSION`,
  `BUILD_DEFINITIONNAME`, `AGENT_OS`, `BUILD_ARTIFACTSTAGINGDIRECTORY` — all shimmed.
- Neither script constructs ADO-format URLs, so no `PIPELINE_URL` support was needed.

## Known gaps / behavioural differences

1. **Hotfix-branch template content not ported** — `team/reporting-hotfix` is absent from this repo; the
   audit-trail logging / pre-build validation steps that live only on that branch must be added once the branch
   is mirrored (or exported from ADO). The `validate-migration` scorecard reports the template as
   "resolved @team/reporting-hotfix" because the validator falls back to the local `main` copy of the file.
2. **Business-hours check** has no GHA equivalent (see *prod gate*).
3. **Required reviewers** must be configured manually on the `prod` environment; the workflow cannot declare them.
4. **PR runs** execute only `compliance_build` (without the metadata upload); the reports job is push/schedule only.
5. **`$(Build.BuildNumber)`** is approximated as `yyyyMMdd.<run_number>`; ADO's `r` counter resets daily whereas
   `run_number` is monotonic.
6. **Build cwd:** the ADO template runs `pip install -r requirements.txt && pytest tests/ && python setup.py sdist
   bdist_wheel` from the checkout root; the GHA step uses `working-directory: services/regulatory-reporting` so it
   finds the service sources. **Pre-existing (preserved):** the sdist/wheel land in `<service>/dist`, not the
   staging directory, so the `regulatory-compliance-pkg` artifact only contains the compliance-metadata JSON.
   Likewise, in `GenerateReports` the metadata/attestation JSON are written to the staging root but only
   `staging/reports` is published. Not fixed during migration.
7. **Runtime:** 82 min average is within the 6 h hosted limit; `timeout-minutes: 90` mirrors ADO.
8. **Validation baselines:** `validation/baselines/regulatory-reporting/` does not exist and there is no service
   source in the repo to measure one from, so the *Artifact Baseline* / *Test Baseline* scorecard checks report
   FAIL. A baseline must be measured from a real run rather than invented.

## Secrets / variables required

| Name | Kind | Source (ADO) |
|---|---|---|
| `COMPLIANCE_STORE_TOKEN` | secret | VG 206 |
| `COMPLIANCE_STORE_CERT_THUMBPRINT` | secret | VG 206 |
| `REPORTING_DB_CONNECTION_STRING` | secret (environment `prod`) | VG 209 |
| `COMPLIANCE_STORE_URL` | variable | VG 206 (`https://compliance-store.contoso-financial.com/api/v2`) |
| `REPORTING_SMTP_SERVER` | variable | VG 209 (`smtp.contoso-financial.com`) |
| `REPORTING_DISTRIBUTION_LIST` | variable | VG 209 (`reg-reports@contoso-financial.com`) |
| `PIP_INDEX_URL` | variable | VG 201 (`https://pkgs.contoso-financial.com/pypi/simple/`) |

Repository settings: environment `prod` with 2 required reviewers; Actions artifact retention ≥ 365 days.
