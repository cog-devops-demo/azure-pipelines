# `risk-batch-ci`: ADO to GHA mapping

| Field | Value |
| --- | --- |
| Pipeline | `risk-batch-ci` |
| ADO ID | `104` |
| Category | `1 central-template consumer` |
| Owner | `team-quant` |
| Stack | Python 3.11 |
| ADO template branch | `staging/preprod` |
| GHA workflow | `.github/workflows/risk-batch-ci.yml` |
| ADO snapshot | 38 runs; last run `2026-03-15` |

> **ADO MCP note:** azure-devops-mcp server failed to initialise (stdio process exited at startup) — expansion was done manually from `staging/preprod` (fetched from upstream COG-GTM/azure-pipelines, since the branch does not exist on cog-devops-demo) and cross-checked against `docs/samples/ado-api-responses.json`.

| Source | Use |
| --- | --- |
| `docs/pipeline-inventory-report.md:40` | Inventory classification, owner, template branch, and migration disposition |
| `docs/samples/ado-api-responses.json` — pipeline ID `104` | ADO definition metadata, triggers, variable groups `201`, `205`, `208`, retention, and latest-run snapshot |
| `services/risk-batch/azure-pipelines.yml` | ADO pipeline composition and parameter values |
| `git show staging/preprod:templates/...` | Template expansion for build, test, and release behavior |
| `git diff main staging/preprod -- templates/` | Branch-unique changes, including retry logic, preprod stamp, and `artifact-registry` naming |
| `build-tools/scripts/{publish_artifact,normalize_test_results,notify_release_orchestrator,generate_attestation}.py` | Integration behavior and environment-variable compatibility |

The GHA workflow is the source of truth for the target behavior. The ADO side was expanded from `services/risk-batch/azure-pipelines.yml` and the `staging/preprod` versions of `templates/build/build-python.yml`, `templates/test/run-tests.yml`, and `templates/release/release-standard.yml`.

## Trigger mapping

| ADO | GHA |
| --- | --- |
| Push to `main`; path filter `services/risk-batch/**` | Push to `main`; paths `services/risk-batch/**` and `.github/workflows/risk-batch-ci.yml` |
| No pull-request trigger | Pull requests targeting `main`; same paths as push |
| No branch-glob broadening | No branch-glob broadening is needed |

The workflow-file path is an intentional addition so changes to the migration itself run CI. Pull-request runs are validation-only; deployment is separately gated below.

## Stage to job mapping

| ADO stage/job | ADO details | GHA job | GHA details |
| --- | --- | --- | --- |
| `Build` / `build` | Display name `Build risk-batch`; central build and test templates | `build` | `runs-on: ubuntu-latest`; contains the inlined build and test steps |
| `Deploy_dev` / `deploy` | From `release-standard.yml`; display name `Deploy to dev`; deployment job; environment `dev` | `deploy_dev` | `needs: build`; `environment: dev`; runs only on a push to `main` |

## Step-by-step task mapping

The table follows execution order after template expansion: `build-python.yml`, `run-tests.yml`, then `release-standard.yml`. Resolved values are `pythonVersion: 3.11`, `requirementsFile: services/risk-batch/requirements.txt`, `artifactName: risk-batch-dist`, `runTests: true`, `enableLinting: true`, `publishArtifacts: true`, `testRetryCount: 3`, `testFramework: pytest`, `testResultsDir: $(Build.ArtifactStagingDirectory)/test-results`, `environment: dev`, `deployStrategy: rolling`, `requireApproval: false`, and `notifyReleaseOrchestrator: true`.

| # | Expanded ADO step | Resolved parameters / behavior | GHA step name and action/run |
| ---: | --- | --- | --- |
| 1 | `UsePythonVersion@0` — `Use Python ${{ parameters.pythonVersion }}` | `pythonVersion: 3.11` | **Use Python 3.11** — `actions/setup-python@v5`, `python-version: 3.11` |
| 2 | Script — `Install dependencies` | `requirementsFile: services/risk-batch/requirements.txt` | **Install dependencies** — upgrade `pip setuptools wheel`; install `"$GITHUB_WORKSPACE/$REQUIREMENTS_FILE"` |
| 3 | Script — `Run linting checks` | `enableLinting: true` | **Run linting checks** — install `flake8 black mypy`; run `flake8 src/ --max-line-length=120` and `black --check src/` |
| 4 | Script — `Run tests with coverage (retry-enabled)` | `runTests: true`; `testRetryCount: 3`; pytest with coverage and `pytest-rerunfailures` | **Run tests with coverage (retry-enabled)** — run pytest with JUnit XML, coverage XML, `--reruns 2`, and the three-attempt shell retry loop |
| 5 | `PublishTestResults@2` — build results | Results file `$(Build.ArtifactStagingDirectory)/test-results.xml`; `condition: always()` | **Publish test results (build-python)** — `actions/upload-artifact@v4` as `risk-batch-build-test-results`; `if: always()` |
| 6 | Script — `Build distribution` | `publishArtifacts: true`; `artifactName: risk-batch-dist` | **Build distribution** — `python setup.py sdist bdist_wheel`; copy `dist/` into staging |
| 7 | `PublishBuildArtifacts@1` — `Upload artifacts` | Publish `$(Build.ArtifactStagingDirectory)` as `risk-batch-dist` | **Upload artifacts** — `actions/upload-artifact@v4`, name `${{ env.ARTIFACT_NAME }}` |
| 8 | Script — `Register artifact in artifact-registry` | `publishArtifacts: true`; registry `artifact-registry`; build ID from `Build.BuildId` | **Register artifact in artifact-registry (Artifactory)** — run `build-tools/scripts/publish_artifact.py`; `if: github.event_name == 'push'` |
| 9 | Script — `Stamp preprod validation marker` | Present only in `staging/preprod` template | **Stamp preprod validation marker** — write `BUILD_BUILDID` to `preprod-stamp.txt` in staging |
| 10 | Script — `Create test results directory` | `testResultsDir: $(Build.ArtifactStagingDirectory)/test-results` | **Create test results directory** — `mkdir -p "$BUILD_ARTIFACTSTAGINGDIRECTORY/test-results"` |
| 11 | Script — `Run pytest` | `testFramework: pytest`; `--tb=short` | **Run pytest** — run `pytest tests/ --junitxml=.../test-results/results.xml --tb=short` |
| 12 | `PublishTestResults@2` — test-template results | `publishResults: true`; `failOnTestFailure: true`; `testResultsDir` as above; `condition: always()` | **Publish test results (run-tests)** — `actions/upload-artifact@v4` as `risk-batch-test-results`; `if: always()` |
| 13 | Script — `Normalize test results` | Input `testResultsDir`; output `$(Build.ArtifactStagingDirectory)/normalized-results.json`; `condition: always()` | **Normalize test results** — run `build-tools/scripts/normalize_test_results.py`; `if: always()` |
| 14 | `download: current` — artifact `risk-batch-dist` | `environment: dev`; artifact `risk-batch-dist` | **Download `${{ env.ARTIFACT_NAME }}`** — `actions/download-artifact@v4` |
| 15 | Script — `Execute deployment` | `environment: dev`; `deployStrategy: rolling` | **Execute deployment** — echo deployment of `risk-batch-dist` to `dev` and `Strategy: rolling` |
| 16 | Script — `Notify release-orchestrator` | `notifyReleaseOrchestrator: true`; service `risk-batch-dist`; environment `dev`; status `success` | **Notify release-orchestrator (D2)** — run `build-tools/scripts/notify_release_orchestrator.py` |
| 17 | Script — `Generate compliance attestation` | Artifact `risk-batch-dist`; environment `dev` | **Generate compliance attestation** — run `build-tools/scripts/generate_attestation.py` |

ADO implicitly checks out the repository for the build job. The GHA build and deployment jobs both check out explicitly; the deployment checkout is required because the release script paths reference `build-tools`.

## Variable mapping

| ADO variable or predefined value | GHA equivalent | Notes |
| --- | --- | --- |
| `artifactName` | `ARTIFACT_NAME` | `risk-batch-dist` |
| `templates_branch` | Eliminated | Templates are inlined in `.github/workflows/risk-batch-ci.yml` |
| `Build.SourceBranch` | `github.ref` via `BUILD_SOURCEBRANCH` | Preserves the ADO-style variable for helper scripts |
| `Build.SourceVersion` | `github.sha` via `BUILD_SOURCEVERSION` | |
| `Build.BuildId` | `github.run_id` via `BUILD_BUILDID` | |
| `Build.DefinitionName` | `github.workflow` via `BUILD_DEFINITIONNAME` | |
| `Build.RequestedFor` | `github.actor` via `BUILD_REQUESTEDFOR` | |
| `Build.ArtifactStagingDirectory` | `$RUNNER_TEMP/staging` via `BUILD_ARTIFACTSTAGINGDIRECTORY` | Set per job through `GITHUB_ENV`; the `runner` context is not available in top-level `env` |
| `Build.SourcesDirectory` | `$GITHUB_WORKSPACE` | |
| `Agent.Name` | `runner.name` via `AGENT_NAME` | Set on the artifact-registration step |
| `Agent.OS` | `runner.os` via `AGENT_OS` | Set on the attestation step |
| New `PIPELINE_URL` | `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` | Used by D2 notification; the helper retains its ADO URL fallback |
| Variable groups 201, 205, 208 | No mapping today | `shared-ci-secrets` (201), `artifact-registry-credentials` (205), and `risk-batch-config` (208) are not consumed by any expanded template step. When real credentials are wired in, use `${{ secrets.* }}` on the `dev` environment; suggested names include `ARTIFACT_REGISTRY_TOKEN`, `ARTIFACT_REGISTRY_USERNAME`, `RELEASE_ORCHESTRATOR_TOKEN`, and `RISK_BATCH_CONFIG` |

## Condition mapping

| ADO condition | GHA condition | Reason |
| --- | --- | --- |
| Deploy stage had no condition because `requireApproval: false` | `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` on `deploy_dev` | ADO only ran this pipeline on main pushes; pull-request runs must not deploy |
| No explicit condition on artifact registration | `if: github.event_name == 'push'` | Preserve push-only Artifactory registration |
| `condition: always()` on build `PublishTestResults@2` | `if: always()` on **Publish test results (build-python)** | Upload results even when tests fail |
| `condition: always()` on test-template `PublishTestResults@2` | `if: always()` on **Publish test results (run-tests)** | Upload results even when tests fail |
| `condition: always()` on `Normalize test results` | `if: always()` on **Normalize test results** | Preserve normalization after test failure |

## Integration points

| Integration | ADO behavior | GHA mapping |
| --- | --- | --- |
| Artifactory | `publish_artifact.py --registry artifact-registry` | Same helper and registry name, with the `staging/preprod` naming; current helper writes a manifest rather than calling a live registry |
| D2 / release orchestrator | `notify_release_orchestrator.py` after deployment | Same helper; it now prefers `PIPELINE_URL` and falls back to the ADO URL construction, so the helper remains backward compatible |
| Compliance attestation | `generate_attestation.py` writes an attestation for the deployment | Same helper; output is uploaded as artifact `risk-batch-dev-attestation` |
| Test results | Two `PublishTestResults@2` tasks: build-template XML and run-tests-template XML glob | Two `actions/upload-artifact@v4` steps: `risk-batch-build-test-results` and `risk-batch-test-results`; GHA has no native test tab. `dorny/test-reporter@v1` is an optional follow-up |

## Known gaps and intentional differences

- **PyPI dependency:** `pytest-junitxml` in the ADO template does not exist on PyPI. `pip index versions` was verified to return no matching distribution, so it is dropped; JUnit XML output is built into pytest. The ADO step would fail at `pip install`.
- **Working directory:** `services/risk-batch` is the GHA working directory because the templates use root-relative `src/` and `tests/`, while `requirementsFile` points into the service directory.
- **Working directory vs `projectDirectory`:** `main`'s templates now take a `projectDirectory: services/risk-batch` parameter; the `staging/preprod` templates do not. The job-level `working-directory: services/risk-batch` gives the same effect.
- **Pre-existing duplicate test run:** The retry-enabled pytest run in `build-python.yml` and the plain pytest run in `run-tests.yml` are both preserved.
- **Test baseline:** `validation/baselines/risk-batch/test-counts.json` (measured from ADO build 34) expects 12 tests — the same 6-test suite run twice, once per pytest step. This is why both pytest runs must stay.
- **Deployment checkout:** ADO deployment jobs do not check out source, but `release-standard.yml` references `$(Build.SourcesDirectory)/build-tools`. GHA checks out explicitly in `deploy_dev`.
- **R2:** `staging/preprod` is unmaintained. Its retry loop and preprod stamp are now inlined, so the GHA workflow has no branch dependency.
- **R4:** `services/risk-batch/pipeline-fragments/build-python-local.yml` is unreferenced by pipeline 104 and was not used.
- **Glob handling:** `**` globs were replaced where the GHA steps run; none are needed in the run steps.
- **Retention:** ADO retains builds for 60 days; GHA uses the repository default retention.

## Secrets required

None today. All integrations are echo/file-writing stubs and no variable-group values are consumed by the expanded steps.

Future environment secrets should be added to the GitHub `dev` environment as needed:

- `ARTIFACT_REGISTRY_TOKEN`
- `ARTIFACT_REGISTRY_USERNAME`
- `RELEASE_ORCHESTRATOR_TOKEN`
- `RISK_BATCH_CONFIG`

The GitHub environment `dev` must exist (R5).

## Validation

| Check | Result |
| --- | --- |
| `actionlint` | Clean |
| `validation/scripts/validate_migration.py` | 100% (7/7) |
| `risk-batch-ci` build job on the PR | Green (lint, both pytest runs, sdist/wheel, uploads) |
