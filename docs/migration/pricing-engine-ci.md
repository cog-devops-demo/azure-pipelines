# pricing-engine-ci — ADO → GitHub Actions mapping

| | Azure DevOps | GitHub Actions |
| --- | --- | --- |
| Definition | `services/pricing-engine/azure-pipelines.yml` (ADO ID 101 in the inventory; live definition ID 1 in `danagajewski/danagajewski-demo`, folder `\azure-pipelines-migration`) | `.github/workflows/pricing-engine-ci.yml` |
| Templates | `shared-ci-platform@main` (`067a3c2f`): `templates/build/build-dotnet.yml`, `templates/test/run-tests.yml`, `templates/release/release-standard.yml` | inlined — the template steps are expanded into three jobs |
| Reference run | run 11 (`succeeded`, source `d23e86d`, templates `main@067a3c2f`) | run [34392788134](https://github.com/cog-devops-demo/azure-pipelines/actions/runs/34392788134) (`success`, same source tree + this workflow) |

## What the pipeline is for

Build the .NET 8 `pricing-engine` service in `Release`, run its xUnit tests with
coverage, publish the web project into a `pricing-engine-drop` artifact, register that
artifact in Artifactory, and — only for `main` — deploy it to the `dev` environment,
notify D2 (release orchestrator) and write a compliance attestation. It is the only
service pipeline that consumes central templates from `main`, so it has no
branch-drift entanglement and could be ported directly.

## Live ADO state (checked via the ADO REST API with the `azure-devops-mcp` service principal)

- Definition `pricing-engine-ci` (id 1, revision 1, `enabled`) points at GitHub repo
  `cog-devops-demo/azure-pipelines`, YAML `services/pricing-engine/azure-pipelines.yml`,
  pool `Azure Pipelines` / `ubuntu-latest`. Triggers are YAML-defined
  (`settingsSourceType: 2`); no pipeline-level variables or variable groups are attached
  in the live definition (the inventory's R6 var-group flag comes from the 2026-03 API
  snapshot, not the current definition).
- Template repo `danagajewski-demo/shared-ci-platform` has all eight branches from the
  inventory; the pipeline pins `main` (`067a3c2f`).
- **Template drift vs. this repo:** `build-dotnet.yml` on ADO `main` restores with
  `DotNetCoreCLI@2 restore`; the copy in this repo still uses
  `NuGetToolInstaller@1` + `NuGetCommand@2`. Run 5 failed on exactly that
  (`NuGetCommand@2` needs mono on ubuntu-24.04); the template was fixed on ADO `main`
  and run 11 passed. The workflow follows the live template (`dotnet restore`).
- Runs: 5 failed (NuGet/mono), 11 succeeded (branch with the .NET scaffold),
  15 failed on `main` with `No files matched the search pattern` — **`main` contains no
  .NET source under `services/pricing-engine/`**, only the pipeline YAML. The GHA
  workflow will fail identically on `main` until the service source is present.

## Trigger

| ADO | GHA | Note |
| --- | --- | --- |
| `trigger.branches: main, release/*` + `paths: services/pricing-engine/**` | `on.push.branches: [main, 'release/**']`, same path filter | `release/*` in ADO matches nested refs; `release/**` is the GHA equivalent |
| no `pr:` block → ADO default PR validation for GitHub repos | `on.pull_request` with the same path filter | intent kept (PRs build), scoped to the service paths |
| — | `.github/workflows/pricing-engine-ci.yml` added to both path filters | so changes to the workflow itself are exercised |
| — | `workflow_dispatch` | manual runs; ADO allowed manual queueing implicitly |

## Stage / job mapping

### `Build` → job `build` (from `build-dotnet.yml@main`)

| ADO step | GHA step |
| --- | --- |
| `UseDotNet@2` sdk `8.0.x` | `actions/setup-dotnet@v4` `dotnet-version: 8.0.x` |
| `DotNetCoreCLI@2 restore` `services/pricing-engine/**/*.sln` | `dotnet restore services/pricing-engine/PricingEngine.sln` (glob resolved to the single solution) |
| `DotNetCoreCLI@2 build --configuration Release --no-restore` | `dotnet build "$SOLUTION" --configuration Release --no-restore` |
| `DotNetCoreCLI@2 test` `**/*Tests/*.csproj` `--collect:"XPlat Code Coverage"` (template default `runTests: true`) | `dotnet test tests/PricingEngine.Tests/PricingEngine.Tests.csproj --no-build --logger trx --collect:"XPlat Code Coverage"` |
| `DotNetCoreCLI@2 publish` `publishWebProjects: true` `--output $(Build.ArtifactStagingDirectory)` (ADO appends the project name → `…/a/PricingEngine/`) | `dotnet publish src/PricingEngine/PricingEngine.csproj --no-build --output "$BUILD_ARTIFACTSTAGINGDIRECTORY/PricingEngine"` |
| `PublishBuildArtifacts@1` `$(Build.ArtifactStagingDirectory)` → `pricing-engine-drop` | `actions/upload-artifact@v4` name `pricing-engine-drop`, path `$BUILD_ARTIFACTSTAGINGDIRECTORY` |
| `script: publish_artifact.py --name … --registry Artifactory --build-id $(Build.BuildId)` | same script, `--build-id "$GITHUB_RUN_ID"`; runs **before** upload so the manifest lands inside the artifact (in ADO the manifest is written after upload and is therefore *not* in the drop — see gaps) |
| — | `upload-artifact` `pricing-engine-test-results` (`*.trx`) and `pricing-engine-code-coverage` — ADO keeps these as test-run attachments; GHA has no test-run store |

### `Test` → job `test` (from `run-tests.yml@main`, `testFramework: generic`)

| ADO step | GHA step |
| --- | --- |
| `mkdir -p $(Build.ArtifactStagingDirectory)/test-results` | same |
| *(no framework step for `generic`)* | `download-artifact pricing-engine-test-results` into that directory |
| `PublishTestResults@2` JUnit `**/*.xml`, `condition: always()` | no equivalent task; the `.trx` is preserved as an artifact |
| `normalize_test_results.py --input-dir … --output …/normalized-results.json`, `always()` | same script, `if: always()`, output uploaded as `pricing-engine-normalized-results` |

With `testFramework: generic` this stage never runs tests in ADO; the real tests run in
`Build`. The workflow keeps that shape (tests in `build`, `test` = collect + normalize)
rather than running the suite twice.

### `Deploy_dev` → job `deploy-dev` (from `release-standard.yml@main`, `environment: dev`, `requireApproval: true`)

| ADO | GHA |
| --- | --- |
| `dependsOn` Test (implicit, stage order) | `needs: test` |
| `condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))` | `if: github.ref == 'refs/heads/main'` (success of `needs` is implicit) |
| `deployment:` job, `environment: dev` (approval check) | `environment: dev` — **approvals live in repo Settings → Environments → dev → Required reviewers**; the environment does not exist in this repo yet (`GET /environments` → 0) |
| `strategy: runOnce` | plain job (single run) |
| `download: current, artifact: pricing-engine-drop` | `actions/download-artifact@v4` |
| `Execute deployment` echo (rolling) | same |
| `notify_release_orchestrator.py … --status success` | same, `--build-id "$GITHUB_RUN_ID"`; `PIPELINE_RUN_URL` env overrides the ADO `_build/results` URL with the Actions run URL |
| `generate_attestation.py` | same; output uploaded as `pricing-engine-dev-attestation` |
| *no checkout* (deployment jobs do not check out sources by default) | `actions/checkout@v4` added — the ADO template references `$(Build.SourcesDirectory)/build-tools/scripts/*.py`, which would not exist in a deployment job; this stage has been `skipped` in every live run so the bug never surfaced |

## Variables

| ADO | GHA |
| --- | --- |
| `buildConfiguration`, `artifactName` (pipeline variables) | workflow `env` `BUILD_CONFIGURATION`, `ARTIFACT_NAME` |
| `$(Build.BuildId)` | `$GITHUB_RUN_ID` |
| `Build.SourceBranch`, `Build.SourceVersion`, `Build.DefinitionName`, `Build.RequestedFor`, `System.TeamFoundationCollectionUri`, `System.TeamProject` — read by the helper scripts | mapped in workflow `env` to `github.ref`, `github.sha`, `github.workflow`, `github.actor`, `github.server_url`, `github.repository` |
| `Agent.Name`, `Agent.OS`, `Build.ArtifactStagingDirectory` | set per job in the `Map ADO agent variables` step from `$RUNNER_NAME`, `$RUNNER_OS`, `$RUNNER_TEMP/a` (the `runner` context is not available in workflow/job-level `env`) |

## Equivalence evidence

Same source tree (`d23e86d`, the scaffold branch) built by both systems:

| Check | ADO run 11 | GHA run 34392788134 |
| --- | --- | --- |
| restore / build | succeeded | succeeded |
| unit tests | `Passed! Failed: 0, Passed: 36, Total: 36`, cobertura attachment | identical line, cobertura uploaded |
| publish output | `/home/vsts/work/1/a/PricingEngine/` | `$RUNNER_TEMP/a/PricingEngine/` (8 files: `PricingEngine`, `.dll`, `.pdb`, `.deps.json`, `.runtimeconfig.json`, `.staticwebassets.endpoints.json`, `appsettings.json`, `web.config`) |
| Artifactory registration | `Manifest written to: /home/vsts/work/1/a/pricing-engine-drop-manifest.json` | `Manifest written to: /home/runner/work/_temp/a/pricing-engine-drop-manifest.json` |
| artifact | `pricing-engine-drop` | `pricing-engine-drop` (52 KB) |
| Test stage | `PublishTestResults`: no `*.xml` found; normalize ran | `Normalized 0 test result files` |
| Deploy stage | skipped (branch ≠ main) | skipped (branch ≠ main) |

`deploy-dev` was exercised locally (scripts run with the workflow's env): D2 notify
`OK`, attestation written and "uploaded".

Validation scripts (`validation/scripts/compare_artifacts.py`,
`compare_test_counts.py`) **fail** against `validation/baselines/pricing-engine/*`
(expects 12 files / 5–50 MB / 187 tests; actual 8 files / 0.11 MB / 36 tests). The
baselines date from 2024-08 and describe a different build of the service than the
scaffold in `d23e86d`; they would fail the ADO output just the same and need
re-baselining, not a workflow change.

## Gaps and follow-ups

1. **No source on `main`.** Both the ADO pipeline and this workflow fail at restore on
   `main`. Land the service source (the scaffold in `d23e86d`) or point the pipeline at
   the repo that has it.
2. **`dev` environment + required reviewers** must be created in GitHub before the
   `deploy-dev` job gates as the ADO approval check did.
3. **Test results publishing.** ADO's `PublishTestResults@2` had nothing to publish
   (`generic` framework, trx not JUnit). The workflow keeps parity (trx as an artifact,
   normalizer sees 0 suites). To make `normalize_test_results.py` useful, add
   `JunitXml.TestLogger` to the test project and log `junit` into the results dir.
4. **Manifest placement.** Registering before upload means `pricing-engine-drop` now
   includes `pricing-engine-drop-manifest.json`; in ADO it was left on the agent.
   Consumers that enumerate the drop should expect one extra JSON file.
5. **Ownership** is still `unknown` (inventory R1); `shared-ci-platform` best-effort.
6. Local template copy `templates/build/build-dotnet.yml` is behind ADO `main`
   (NuGet vs. `dotnet restore`) — sync it or drop it once templates become reusable
   workflows.
