# risk-batch-ci ADO-to-GHA mapping

## Overview

| Field | ADO | GitHub Actions |
| --- | --- | --- |
| Pipeline | `risk-batch-ci` | `risk-batch-ci` |
| Pipeline ID | 104 | — |
| Live definition | 6 in `danagajewski/danagajewski-demo` | — |
| Category | 1 | — |
| Owner team | `team-quant` | — |
| Agent pool | `ubuntu-latest` | `ubuntu-latest` |
| Template branch | `staging/preprod` at commit `a3eeb522` | Templates inlined |

The source pipeline is `services/risk-batch/azure-pipelines.yml`. The migration
keeps its Python 3.11 build, lint, two pytest executions, distribution
artifacts, Artifactory registration, dev deployment, release-orchestrator
notification, and compliance attestation.

The MCP server available for this session is bound to a different organization
(`shawn0864`). Template verification was therefore performed against the Azure
DevOps REST API for `danagajewski/danagajewski-demo`: definition 6, run 95,
the preview of expanded YAML, and the three template files fetched from
`shared-ci-platform@staging/preprod`. The fetched template commit was
`a3eeb522`. Those templates are identical to this repository's `templates/`
copies except that release-standard's D2 step is named
`Notify release-orchestrator` in the fetched version. The live branch has no
retry logic.

## Trigger mapping

| ADO trigger | GHA trigger |
| --- | --- |
| Push to `main` | Push to `main` |
| `services/risk-batch/**` | `services/risk-batch/**` |
| — | Pull request to `main` |
| — | `.github/workflows/risk-batch-ci.yml` |
| — | `build-tools/scripts/**` |
| — | `workflow_dispatch` |

The pull-request trigger and manual dispatch are intentional additions. The
workflow-file and shared build-script paths are included so changes to the
migration workflow or its integration scripts validate the pipeline.

## Stage to job mapping

| ADO stage | ADO job | GHA job | GHA runner/environment |
| --- | --- | --- | --- |
| `Build` | `build` | `build` (`Build risk-batch`) | `ubuntu-latest` |
| `Deploy_dev` | deployment job from `release-standard.yml` | `deploy_dev` (`Deploy to dev`) | `ubuntu-latest`, environment `dev` |

## Task-by-task mapping

### `build`

| ADO task/template step | GHA step | Inputs and translation |
| --- | --- | --- |
| `checkout: self` (implicit) | `actions/checkout@v4` | Checks out the repository. |
| `UsePythonVersion@0` | `actions/setup-python@v5` | `pythonVersion: 3.11` becomes `${{ env.PYTHON_VERSION }}`. |
| Agent-provided `$(Build.ArtifactStagingDirectory)` | `Create artifact staging directory` | Uses `$BUILD_ARTIFACTSTAGINGDIRECTORY`, set to `${{ runner.temp }}/staging`. |
| `build-python.yml` — `Install dependencies` | `Install dependencies` | Installs pip, setuptools, wheel, then `services/risk-batch/requirements.txt`. |
| `build-python.yml` — `Run linting checks` | `Run linting checks` | Runs flake8 with max line length 120 and `black --check src/` in `services/risk-batch`; installs mypy as ADO does but does not run it. |
| `build-python.yml` — `Run tests with coverage` | `Run tests with coverage` | Runs pytest with JUnit output at `test-results.xml` and coverage XML at `coverage.xml`. |
| `PublishTestResults@2` in `build-python.yml` | `Publish test results (build)` | Uploads `risk-batch-test-results`; runs with `if: always()`. |
| `build-python.yml` — `Build distribution` | `Build distribution` | Runs `setup.py sdist bdist_wheel` and copies `dist/` into staging. |
| `PublishBuildArtifacts@1` | `Upload artifacts` | Publishes `risk-batch-dist` from staging before later test/integration steps. |
| `build-python.yml` — `Register artifact in Artifactory` | `Register artifact in Artifactory` | Push-only; invokes `publish_artifact.py` with Artifactory, artifact name, and `github.run_id`; ADO variables are supplied as environment shims. |
| `run-tests.yml` — `Create test results directory` | `Create test results directory` | Creates staging `test-results`. |
| `run-tests.yml` — `Run pytest` | `Run pytest` | Runs pytest with `results.xml` and `--tb=short`. |
| `PublishTestResults@2` in `run-tests.yml` | `Publish test results (run-tests)` | Uploads `risk-batch-run-tests-results`; runs with `if: always()`. |
| `run-tests.yml` — `Normalize test results` | `Normalize test results` | Writes normalized JSON from staging test XML; runs with `if: always()`. |
| — | `Upload normalized test results` | Extra GHA parity artifact `risk-batch-normalized-results`; runs with `if: always()`. |

The extra normalized-results upload is intentional: GitHub Actions has no
native equivalent of the repository's normalized cross-framework result
consumer, so the generated JSON is retained as an artifact.

### `deploy_dev`

| ADO task/template step | GHA step | Inputs and translation |
| --- | --- | --- |
| `checkout: self` | `actions/checkout@v4` | Checks out the repository on the deployment runner. |
| Agent-provided `$(Build.ArtifactStagingDirectory)` | `Create artifact staging directory` | Creates fresh-runner staging at `${{ runner.temp }}/staging`. |
| `DownloadBuildArtifacts@1` | `Download artifacts` | Downloads `risk-batch-dist` to `${{ runner.temp }}/pipeline-workspace/risk-batch-dist`. |
| `release-standard.yml` — `Execute deployment` | `Execute deployment` | Preserves the rolling strategy message and dev target. |
| `release-standard.yml` — `Notify release-orchestrator` | `Notify D2 (release-orchestrator)` | Calls `notify_release_orchestrator.py`; GHA URL is provided through `PIPELINE_URL`; `Build.RequestedFor` is shimmed. |
| `release-standard.yml` — `Generate compliance attestation` | `Generate compliance attestation` | Calls `generate_attestation.py` with branch, commit, workflow, and runner OS shims. |
| Compliance artifact publication | `Upload compliance attestation` | Uploads `risk-batch-dev-attestation` from `risk-batch-dist-attestation.json`. |

## Variable mapping

| ADO variable | GHA equivalent |
| --- | --- |
| `artifactName` | `ARTIFACT_NAME: risk-batch-dist` |
| `templates_branch` | Dropped because the templates are inlined. |
| `risk-batch-config/RISK_DB_CONNECTION_STRING` | `secrets.RISK_DB_CONNECTION_STRING`, exposed as a build job environment variable. |
| `pythonVersion` | `PYTHON_VERSION: '3.11'` |
| `projectDirectory` | `PROJECT_DIRECTORY: services/risk-batch` |
| `requirementsFile` | `REQUIREMENTS_FILE: services/risk-batch/requirements.txt` |

### ADO-to-GHA environment shims

| ADO variable | GHA value |
| --- | --- |
| `Build.ArtifactStagingDirectory` | `BUILD_ARTIFACTSTAGINGDIRECTORY=$RUNNER_TEMP/staging` (exported via `$GITHUB_ENV` by the first step of each job) |
| `Build.SourceBranch` | `BUILD_SOURCEBRANCH=${{ github.ref }}` |
| `Build.SourceVersion` | `BUILD_SOURCEVERSION=${{ github.sha }}` |
| `Build.BuildId` | `${{ github.run_id }}` command argument |
| `Build.RequestedFor` | `BUILD_REQUESTEDFOR=${{ github.actor }}` |
| `System.TeamFoundationCollectionUri` + `System.TeamProject` | Not shimmed; superseded by `PIPELINE_URL` (script falls back to them only when `PIPELINE_URL` is unset) |
| `Build.DefinitionName` | `BUILD_DEFINITIONNAME=${{ github.workflow }}` |
| `Agent.OS` | `AGENT_OS=${{ runner.os }}` |
| `Agent.Name` | `AGENT_NAME=${{ runner.name }}` |
| Pipeline result URL | `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` |

`notify_release_orchestrator.py` now prefers the explicit `PIPELINE_URL` and
otherwise keeps its existing ADO URL concatenation for backward compatibility.

## Condition mapping

| ADO behavior | GHA behavior | Rationale |
| --- | --- | --- |
| `Deploy_dev` has no stage condition and ran on PR validation builds | `deploy_dev` runs only when the event is a push to `refs/heads/main` | Intentional safety gate; the `dev` environment remains configured on the job. |
| `condition: always()` on test result publication | `if: always()` | Preserved for both JUnit uploads, normalization, and attestation publication. |
| Artifactory registration follows the build | Push-only `if: github.event_name == 'push'` | Intentional: registration is not performed for pull requests. |

## Integration points

- **Artifactory:** `publish_artifact.py` is invoked with `--registry
  Artifactory` and the `risk-batch-dist` artifact name.
- **D2/release-orchestrator:** `notify_release_orchestrator.py` is invoked
  during dev deployment and now honors the GHA `PIPELINE_URL`.
- **Compliance attestation:** `generate_attestation.py` writes
  `risk-batch-dist-attestation.json` to staging, and the deployment job uploads
  it as `risk-batch-dev-attestation`.

## Test results

GitHub Actions does not provide a native test-results viewer equivalent to
`PublishTestResults@2`. The workflow uploads two JUnit artifacts:
`risk-batch-test-results` and `risk-batch-run-tests-results`. Each contains six
testcases, for 6 + 6 = 12 total testcases matching the two ADO pytest
publishes. The normalized JSON is uploaded separately as the extra
`risk-batch-normalized-results` artifact.

The `risk-batch-dist` artifact is uploaded before the second pytest run and
therefore contains exactly the four ADO files: `test-results.xml`,
`coverage.xml`, `dist/risk_batch-0.1.0-py3-none-any.whl`, and
`dist/risk_batch-0.1.0.tar.gz`.

## Secrets required

- `RISK_DB_CONNECTION_STRING` must be configured as a repository or
  organization secret.
- The GitHub Actions `dev` environment must exist, with its intended
  protection rules and approvals configured.

## Known gaps and notes

1. The inventory claimed retry logic existed only on `staging/preprod`.
   Verification against the live branch found no retry logic. The fetched
   templates equal this repository's `main` templates except for the
   release-orchestrator display name, so there is no retry behavior to port.
2. `pipeline-fragments/build-python-local.yml` is unreferenced and is
   intentionally not ported.
3. There is no native GitHub Actions test-results tab; JUnit files are
   preserved as artifacts.
4. Deployment is skipped on pull requests intentionally.
5. `mypy` is installed but never run, preserving the pre-existing ADO
   behavior.
6. `publish_artifact.py` writes its manifest into the staging directory after
   the `risk-batch-dist` upload, so the manifest is not in that artifact. This
   preserves the ADO ordering.
