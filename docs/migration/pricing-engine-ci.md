# pricing-engine CI migration

| ADO definition | GitHub Actions workflow | Template source |
|---|---|---|
| Pipeline 101: `services/pricing-engine/azure-pipelines.yml` | `.github/workflows/pricing-engine-ci.yml` (`pricing-engine-ci`) | `shared-ci-platform@main`, resolved at ADO commit `47f9464e8b5e3cf62cc41fd457f707a0fdbbdd08` |

The resolved `build-dotnet.yml` and `release-standard.yml` are byte-identical
to this repository's `origin/main`. The resolved `run-tests.yml` differs only
because the local copy has an additional `projectDirectory` parameter for its
pytest branch; that difference is irrelevant to this pipeline's
`testFramework: generic` use.

## Purpose

The workflow preserves the three ADO stages for the pricing-engine .NET 8
build, the generic test-results normalization stage, and the main-branch-only
development deployment stage. It keeps the Artifactory registration, D2
release-orchestrator notification, compliance attestation, test-results
artifact, and code-coverage artifact integration points needed by migration
parity checks.

## Trigger mapping

| ADO | GitHub Actions |
|---|---|
| `main` and `release/*` branch CI trigger | `push.branches: [main, 'release/**']` |
| Service path trigger `services/pricing-engine/**` | Same path under `push.paths`, plus `build-tools/scripts/**` because the jobs call those helpers |
| No ADO pull-request trigger in the source definition | `pull_request` for the service and workflow paths, so changes are validated before merge |
| Manual execution through ADO | `workflow_dispatch` |
| Hosted `ubuntu-latest` pool | `runs-on: ubuntu-latest` for each job |

The workflow file itself is included in the push and pull-request path filters
so changes to the migration definition can run validation.

## Stage mapping

### Build

| ADO template step | GitHub Actions step |
|---|---|
| `UseDotNet@2` for SDK `8.0.x` | `actions/setup-dotnet@v4` with `DOTNET_VERSION` |
| `DotNetCoreCLI@2 restore` for `services/pricing-engine/**/*.sln` | `dotnet restore "$SOLUTION"` for `services/pricing-engine/PricingEngine.sln` |
| `DotNetCoreCLI@2 build --configuration Release --no-restore` | `dotnet build "$SOLUTION" --configuration "$BUILD_CONFIGURATION" --no-restore` |
| Template unit test execution with coverage collection | `dotnet test` on `PricingEngine.Tests.csproj`, producing a TRX in `$RUNNER_TEMP/test-output` and collecting XPlat coverage |
| `DotNetCoreCLI@2 publish` | `dotnet publish` to `$RUNNER_TEMP/a/PricingEngine` with the same Release/no-build settings |
| `PublishBuildArtifacts@1` as `pricing-engine-drop` | `actions/upload-artifact@v4` as `pricing-engine-drop` |
| `publish_artifact.py --registry Artifactory --build-id $(Build.BuildId)` | Same helper with `--build-id "$GITHUB_RUN_ID"`; its manifest is uploaded as `pricing-engine-drop-manifest` |

The publish output is zipped after publishing with `zipAfterPublish`-equivalent
semantics: the contents of the `PricingEngine` directory are placed at the
root of `PricingEngine.zip`, rather than putting the directory itself inside
the archive. The directory is removed after the zip is created. This preserves
the ADO baseline of one `PricingEngine.zip` artifact file.

ADO's `PublishTestResults@2` is not reproduced as a separate GitHub Actions
operation. The TRX remains available in `pricing-engine-test-results`, which
is the test-named artifact consumed by the parity checker. The coverage output
is retained in `pricing-engine-code-coverage`.

### Test

| ADO template step | GitHub Actions step |
|---|---|
| Create `test-results` directory | `mkdir -p "$RUNNER_TEMP/a/test-results"` |
| `testFramework: generic` | No additional test execution; the ADO generic branch likewise runs no tests in this stage |
| `PublishTestResults@2` | No GHA equivalent; the Build job's TRX artifact is downloaded for normalization |
| `normalize_test_results.py` with `condition: always()` | Same helper with `if: always()` |
| ADO staging output | `pricing-engine-normalized-results` artifact uploaded with `if: always()` |

The normalizer accepts both JUnit XML and VSTest TRX. It skips non-JUnit XML
files such as coverage Cobertura documents with a warning instead of counting
them as empty suites.

### Deploy_dev

| ADO template step | GitHub Actions step |
|---|---|
| `requireApproval: true` and main-branch condition | `if: github.ref == 'refs/heads/main'` plus `environment: dev` |
| Deployment job on `ubuntu-latest` | `deploy-dev` job on `ubuntu-latest` |
| Deployment checkout | Explicit `actions/checkout@v4`; although ADO deployment jobs do not generally checkout by default, this template calls scripts from `$(Build.SourcesDirectory)` |
| `DownloadBuildArtifacts@1` | `actions/download-artifact@v4` for `pricing-engine-drop` |
| Echo deployment using the default `rolling` strategy | Same deployment and strategy echo lines |
| `notify_release_orchestrator.py` / D2 | Same helper with `GITHUB_RUN_ID` as the build identifier |
| `generate_attestation.py` | Same helper with `GITHUB_RUN_ID`, writing to the runner staging directory |
| No ADO artifact upload for the attestation file | `pricing-engine-dev-attestation` upload for the generated JSON |

The `dev` environment does not exist in GitHub yet. Required reviewers must be
configured in **GitHub Settings → Environments → dev** before the workflow is
treated as an approval-equivalent deployment gate.

## Variables and CI context

| ADO predefined variable | GitHub Actions variable | `ci_context.py` function |
|---|---|---|
| `BUILD_SOURCEBRANCH` | `GITHUB_REF` | `source_branch()` |
| `BUILD_SOURCEVERSION` | `GITHUB_SHA` | `source_commit()` |
| `BUILD_DEFINITIONNAME` | `GITHUB_WORKFLOW` | `pipeline_name()` |
| `BUILD_REQUESTEDFOR` | `GITHUB_ACTOR` | `requested_for()` |
| `AGENT_NAME` | `RUNNER_NAME` | `agent_name()` |
| `AGENT_OS` | `RUNNER_OS` | `agent_os()` |
| `BUILD_ARTIFACTSTAGINGDIRECTORY` | `$RUNNER_TEMP/a` | `staging_directory()` |
| `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` + `SYSTEM_TEAMPROJECT` + build ID | `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` + `GITHUB_RUN_ID` | `run_url()` |
| `Build.BuildId` | `GITHUB_RUN_ID` | Workflow argument mapping |

The helper is ADO-first: existing ADO predefined variables continue to win,
then GitHub Actions variables are used, and finally `"unknown"` (or an empty
URL) is returned where appropriate. No ADO-variable compatibility shims are
added to the workflow environment.

## Helper script changes

- Added `build-tools/scripts/ci_context.py` with ADO-first and GitHub Actions
  context resolution.
- Updated `publish_artifact.py`, `notify_release_orchestrator.py`, and
  `generate_attestation.py` to use the shared context without changing their
  payload keys or ADO payload values.
- Extended `normalize_test_results.py` to parse namespaced VSTest TRX counters
  and report `format: "trx"`, while retaining the existing JUnit output shape.
- The normalizer now scans both `.xml` and `.trx` files and warns/skips XML
  files that contain no JUnit `testsuite` elements.

## Gaps and follow-ups

- The GitHub `dev` environment and its required reviewers have not been
  configured yet; `requireApproval: true` is represented by the main-only
  condition and the environment gate.
- The owner remains unknown, as recorded for pipeline 101 in the inventory
  report (§3 and §6). An owner should sign off on behavioral parity.
- Inventory-listed variable groups `shared-ci-secrets` and
  `artifact-registry-credentials` and service connection
  `AzureSubscription-Dev` have no runtime use in this YAML. They should be
  recreated as GitHub environment secrets only if the deploy stops being an
  echo and starts using those integrations.
- Artifactory registration, D2 notification, and attestation helpers are
  stubs that write local files or print success messages. The migration keeps
  their invocation and payload shape; it does not invent external credentials
  or deployment behavior.
