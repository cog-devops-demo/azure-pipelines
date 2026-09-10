# settlement-gateway-classic → GitHub Actions mapping

| | |
|---|---|
| ADO definition | `settlement-gateway-classic` — **classic (designer) build definition**, id `9`, revision 2, `danagajewski/danagajewski-demo` |
| Source of truth | `GET https://dev.azure.com/danagajewski/danagajewski-demo/_apis/build/definitions/9?api-version=7.1` (read live on 2026-09-10) |
| Committed cross-check | `docs/migration/ado-exports/settlement-gateway-classic.json` — identical to the live definition apart from server-side metadata (`_links`, `authoredBy`, `createdDate`, `queue.url`, `repository.properties`, …) |
| Category | Custom inline (Category 4 equivalent) — no YAML, no templates; one phase with seven inline tasks |
| Pool | `Azure Pipelines` (hosted), `agentSpecification: ubuntu-22.04` |
| GHA workflow | `.github/workflows/settlement-gateway-ci.yml` |
| Inventory report | not listed in `docs/pipeline-inventory-report.md` (classic definitions are not discoverable from repo YAML); background in `docs/migration/settlement-gateway-classic.md` |

The workflow file is named `settlement-gateway-ci.yml` rather than `settlement-gateway-classic.yml`
because `validate-migration.yml` maps that basename to the classic export and to the ADO definition
name for the runtime parity check.

## How the definition was read

Classic definitions have no `azure-pipelines.yml`; the REST definition JSON is the pipeline. Tasks are
identified by GUID in `process.phases[].steps[].task.id`:

| Task GUID | Task | Steps |
|---|---|---|
| `33c63b11-352b-45a2-ba1b-54cb568a29ca` | `UsePythonVersion@0` | Use Python 3.11 |
| `e213ff0f-5d5c-4791-802d-52ea3e7be1f1` | `PowerShell@2` | Stamp version and write build manifest; Package and register artifact |
| `6c731c3c-3c68-459a-a5c9-bde6e6595b5b` | `Bash@3` | Install dependencies; Run unit tests |
| `0b0f01ed-7dde-43ff-9cbb-e48954daf9b1` | `PublishTestResults@2` | Publish test results |
| `2ff763a7-ce83-4e1f-bc89-0ae63477cebe` | `PublishBuildArtifacts@1` | Publish build artifact |

Recent live runs (all revision 2): build 235 on `main` succeeded (8/8 tests, artifact
`settlement-gateway-drop`); build 234 on `refs/pull/41/merge` failed at checkout (git fetch of the
merge ref, before any task ran) — a pre-existing ADO-side flake, not a pipeline logic failure.

## Trigger mapping

| ADO (`triggers[]`) | GHA (`on:`) | Notes |
|---|---|---|
| `continuousIntegration`: `+refs/heads/main`, path `+/services/settlement-gateway` | `push.branches: [main]`, `paths: services/settlement-gateway/**` | Workflow file itself added to `paths` so workflow edits self-validate |
| `pullRequest`: `+refs/heads/main`, path `+/services/settlement-gateway`, forks disabled | `pull_request.branches: [main]`, same paths | Fork PRs get no secrets in GHA by default, matching `forks.enabled: false` in spirit |
| `maxConcurrentBuildsPerBranch: 1`, `batchChanges: false` | `concurrency: settlement-gateway-ci-${{ github.ref }}`, `cancel-in-progress: false` | Queues rather than cancels, like ADO |
| `variables.SETTLEMENT_ENV` `allowOverride: true` | `workflow_dispatch.inputs.settlement_env` | Queue-time override becomes a manual-run input |

## Phase → job mapping

| ADO phase | GHA job | Runner | Timeout |
|---|---|---|---|
| `Build settlement gateway` (`Phase_1`, `condition: succeeded()`) | `build` — "Build settlement gateway" | `ubuntu-22.04` (matches `agentSpecification.identifier`) | `timeout-minutes: 60` (`jobTimeoutInMinutes: 60`) |

## Step mapping

| # | ADO task (displayName) | Inputs | GHA step | Translation |
|---|---|---|---|---|
| 0 | implicit checkout | — | `actions/checkout@v4` | |
| 1 | `UsePythonVersion@0` "Use Python 3.11" | `versionSpec: 3.11`, `addToPath: true`, `architecture: x64` | `actions/setup-python@v5` `python-version: 3.11`, `architecture: x64` | `addToPath` is default behaviour |
| — | (agent-provided `$(Build.ArtifactStagingDirectory)`) | — | "Create artifact staging directory" | `mkdir -p $RUNNER_TEMP/staging`, exported as `BUILD_ARTIFACTSTAGINGDIRECTORY` via `$GITHUB_ENV` (fresh runner has no staging dir) |
| 2 | `PowerShell@2` "Stamp version and write build manifest" | `targetType: inline`, `pwsh: true`, `errorActionPreference: stop`, `failOnStderr: false` | `shell: pwsh` run step, script verbatim | `##vso[task.logissue type=error]` → `::error::`; `##vso[task.setvariable variable=settlementVersion]` → `Add-Content $GITHUB_ENV "SETTLEMENTVERSION=…"` |
| 3 | `Bash@3` "Install dependencies" | inline | bash run step, script verbatim | |
| 4 | `Bash@3` "Run unit tests" | inline, `--junitxml=$(Build.ArtifactStagingDirectory)/test-results/junit.xml` | bash run step | `$(Build.ArtifactStagingDirectory)` macro → `$BUILD_ARTIFACTSTAGINGDIRECTORY` |
| 5 | `PublishTestResults@2` "Publish test results" | `JUnit`, `$(Build.ArtifactStagingDirectory)/test-results/*.xml`, `mergeTestResults: true`, `alwaysRun`/`succeededOrFailed()` | `actions/upload-artifact@v4` `settlement-gateway-test-results`, `if: ${{ !cancelled() }}` | No native test tab in GHA; JUnit XML retained as artifact (parity script counts `testcase`s from it) |
| 6 | `PowerShell@2` "Package and register artifact" | inline, `pwsh: true` | `shell: pwsh` run step, script verbatim | `##vso[task.logissue type=warning]` → `::warning::`; `SETTLEMENT_REGISTRY_URL` supplied from `secrets` **only on `push`** |
| 7 | `PublishBuildArtifacts@1` "Publish build artifact" | `PathtoPublish: $(Build.ArtifactStagingDirectory)`, `ArtifactName: settlement-gateway-drop`, `Container`, `succeededOrFailed()` | `actions/upload-artifact@v4` `settlement-gateway-drop`, `path: ${{ runner.temp }}/staging`, `if: ${{ !cancelled() }}` | `if-no-files-found: warn` mirrors ADO's "directory is empty" warning on failed builds |

## Variable mapping

| ADO | GHA | Notes |
|---|---|---|
| `SETTLEMENT_ENV` = `dev` (`allowOverride`) | `env.SETTLEMENT_ENV: ${{ inputs.settlement_env \|\| 'dev' }}` | |
| `system.debug` = `false` | — | GHA equivalent is the `ACTIONS_STEP_DEBUG` repository secret/variable; not a workflow concern |
| `$(Build.SourceBranchName)` / `BUILD_SOURCEBRANCHNAME` | `${{ github.ref_name }}` | see gap 1 |
| `$(Build.BuildId)` / `BUILD_BUILDID` | `${{ github.run_id }}` | version becomes `4.2.<run_id>` (see gap 2) |
| `$(Build.SourcesDirectory)` / `BUILD_SOURCESDIRECTORY` | `${{ github.workspace }}` | |
| `$(Build.ArtifactStagingDirectory)` / `BUILD_ARTIFACTSTAGINGDIRECTORY` | `$RUNNER_TEMP/staging` | |
| `$(Build.SourceBranch)`, `$(Build.SourceVersion)` | `${{ github.ref }}`, `${{ github.sha }}` | shimmed for consistency with the other migrated workflows |
| `settlementVersion` (set via `task.setvariable`, read as `SETTLEMENTVERSION`) | `SETTLEMENTVERSION` in `$GITHUB_ENV` | ADO upper-cases set variables when exposing them as env vars; the package step reads the upper-cased name |
| — | `PIPELINE_URL` | GHA-format run URL, available for helper scripts |

## Condition mapping

| ADO | GHA |
|---|---|
| `condition: succeeded()` (default steps) | default step behaviour |
| `alwaysRun: true` / `succeededOrFailed()` (publish test results, publish build artifact) | `if: ${{ !cancelled() }}` — runs after success or failure but, like `succeededOrFailed()`, not after cancellation |
| `enabled: true` on all steps | all steps present (a disabled classic task would have been omitted) |

## Integration points

| Point | ADO | GHA |
|---|---|---|
| Artifact registry (Artifactory successor) | Inline PowerShell writes `registry-receipt.json`; publishes only when `SETTLEMENT_REGISTRY_URL` is set (unset in the demo → `status: skipped`) | Same script; `SETTLEMENT_REGISTRY_URL` is injected from `secrets.SETTLEMENT_REGISTRY_URL` only on `push` events, so PR builds can never register a package |
| Test results | ADO test run "settlement-gateway unit tests" | `settlement-gateway-test-results` artifact (JUnit XML) |
| Build artifact | `settlement-gateway-drop` (manifest, receipt, zip, `test-results/junit.xml`) | `settlement-gateway-drop` with the same contents |
| D2 / compliance attestation | not used | not applicable |
| Helper scripts (`build-tools/scripts/`) | none called | none — no script changes needed |

## Known gaps / intentional differences

1. **Branch name on pull requests.** ADO builds `refs/pull/<n>/merge`, so `BUILD_SOURCEBRANCHNAME` is
   `merge`; GHA's `github.ref_name` is `<n>/merge`. Both fall through to the `default` case
   (`-dev` suffix) so the derived version suffix is unchanged; the `branch` field in
   `build-manifest.json` differs textually.
2. **Build id.** `4.2.<BUILD_BUILDID>` becomes `4.2.<github.run_id>`; run ids are much larger numbers
   than ADO build ids. The zip file name therefore differs between platforms
   (`settlement-gateway-4.2.235.zip` vs `settlement-gateway-4.2.<run_id>.zip`); the artifact
   *name* `settlement-gateway-drop` is identical, which is what the parity check compares.
3. **Test reporting.** No GHA test tab; results are an artifact. `dorny/test-reporter@v1` could be added
   later if a rendered view is wanted.
4. **`release*` / `hotfix*` branches.** The ADO CI trigger only fires on `main`, so those version
   suffixes are only reachable via manual queueing in ADO; in GHA they are only reachable via
   `workflow_dispatch` on such a branch. Behaviour preserved, not extended.
5. **Fork PRs.** ADO disables fork builds; GHA runs them without secrets. Because the registry URL is
   only injected on `push`, a fork PR still cannot register a package.
6. **PowerShell on Linux.** Both platforms run the inline scripts under PowerShell Core (`pwsh: true`
   in ADO; `shell: pwsh` on the `ubuntu-22.04` GHA image, where pwsh is preinstalled).

## Secrets / variables required in GitHub

| Name | Kind | Required | Purpose |
|---|---|---|---|
| `SETTLEMENT_REGISTRY_URL` | repository secret | optional | Enables package registration on pushes to `main`. When absent the workflow records a `skipped` receipt and emits a warning — identical to the current ADO behaviour, where the variable is not configured. |

## Baselines

`validation/baselines/settlement-gateway/` records ADO build 235 (commit `d768a522`): 8 pytest tests,
`settlement-gateway-drop` with 4 files (5,446 bytes). Advisory only — runtime parity against the live
runs is the equivalence check.
