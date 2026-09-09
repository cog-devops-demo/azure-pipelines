# ops-control-plane-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `ops-control-plane-ci` (ID **109**), `services/ops-control-plane/azure-pipelines.yml` |
| GHA workflow | `.github/workflows/ops-control-plane-ci.yml` |
| Category | 4 — Custom inline (no `resources.repositories`, no `template:` references; predates `templates/build/build-go.yml`) |
| Template branch | none |
| Stack | Go 1.22 (`GoTool@0` → `actions/setup-go@v5`) |
| Pool | `ubuntu-latest` (Microsoft-hosted) → `runs-on: ubuntu-latest` |
| Owner | platform-team |
| Risk flags (inventory) | R11 no template reuse; R6 variable groups; R12 ACR service connection |

## Source verification

- ADO YAML read from `main` and expanded manually. The pipeline is fully inline, so there is
  nothing to resolve: one stage, one job, six steps.
- The `azure-devops-mcp` server could not be reached in this session (the configured org is
  `shawn0864`, not `danagajewski`; the stdio server exited at startup), so
  `pipeline_preview_pipeline_yaml` was not available. The ADO API snapshot in
  `docs/samples/ado-api-responses.json` was used instead: definition 109 is `enabled`, 25 runs
  (24 succeeded / 1 failed), avg 7.8 min, last run 2026-03-13 on `refs/heads/main`.
- No helper scripts in `build-tools/` are called by this pipeline, so none were modified.

## Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger.branches.include: [main]` | `on.push.branches: [main]` | |
| `trigger.paths.include: [services/ops-control-plane/**]` | `on.push.paths: ['services/ops-control-plane/**', '.github/workflows/ops-control-plane-ci.yml']` | GHA path filters support `**` natively (this is not a shell glob). The workflow file itself is added so workflow edits are exercised by CI (ADO has no equivalent: its definition lives beside the sources). |
| *(no PR trigger)* | `on.pull_request` on `main`, same path filter | **Intentional addition** for earlier feedback on PRs. |
| *(manual "Run pipeline" button — implicit in ADO)* | `on.workflow_dispatch` | Preserves the ability to queue a build for any branch. |
| *(no schedule)* | — | |

## Stage / job mapping

| ADO stage → job | GHA job | `needs` | Notes |
|---|---|---|---|
| `Build` ("Build ops-control-plane") → `build_go` ("Go build and test") | `build` ("Build ops-control-plane") | — | Single job. `workingDirectory: $(modulePath)` on every script step → job-level `defaults.run.working-directory: services/ops-control-plane`. |

## Step / task mapping (expanded execution order)

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 0 | implicit `checkout: self` | `actions/checkout@v4` | |
| 1 | `GoTool@0` `version: '1.22'` | `actions/setup-go@v5` `go-version: '1.22'`, `cache: false` | ADO did no module caching; caching is disabled to keep the run shape identical and to avoid a hard failure if `go.sum` is absent. Enable `cache: true` later as an optimisation. |
| 2 | `script` "Download modules": `go mod download && go mod verify` | `run` (same commands) | |
| 3 | `script` "Vet": `go vet ./...` | `run` (same) | |
| 4 | `script` "Run tests": `go test ./... -v -coverprofile=coverage.out` | `run` (same) | `coverage.out` is written to the module dir and — as in ADO — not published. |
| 5 | `script` "Build binary": `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o $(Build.ArtifactStagingDirectory)/ops-control-plane ./cmd/server` | `run` with `mkdir -p "$STAGING_DIR"` then the same `go build` writing to `$STAGING_DIR/ops-control-plane` | `mkdir -p` added because the staging dir does not pre-exist on a GHA runner (ADO creates `Build.ArtifactStagingDirectory` automatically). |
| 6 | `PublishBuildArtifacts@1` `pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: ops-control-plane-binary` | `actions/upload-artifact@v4` `name: ops-control-plane-binary`, `path: ${{ env.STAGING_DIR }}`, `if-no-files-found: error` | Artifact name preserved. |

No `**` shell globs, `publishWebProjects`, or Artifactory / D2 / attestation steps exist in the
source, so none of those translation rules apply.

## Variable mapping

| ADO variable | GHA `env` | Notes |
|---|---|---|
| `GOPATH: $(system.defaultWorkingDirectory)/go` | `GOPATH: ${{ github.workspace }}/go` | `actions/setup-go` honours a pre-set `GOPATH`. |
| `GOBIN: $(GOPATH)/bin` | `GOBIN: ${{ github.workspace }}/go/bin` | GHA `env` values cannot reference sibling keys, so the path is spelled out. |
| `modulePath: services/ops-control-plane` | `MODULE_PATH: services/ops-control-plane` + `defaults.run.working-directory` | |
| `$(Build.ArtifactStagingDirectory)` | `STAGING_DIR: ${{ github.workspace }}/staging` | `runner.temp` is not available in workflow-level `env`, so the staging dir lives under the workspace (outside the Go module dir, so it does not affect `./...` package patterns). |
| `$(Build.SourceBranch)` / `$(Build.SourceVersion)` / `$(Build.BuildId)` | `BUILD_SOURCEBRANCH` / `BUILD_SOURCEVERSION` / `BUILD_BUILDID` shims + `PIPELINE_URL` | Not consumed by any step today; provided so any future `build-tools/scripts/*` call runs unmodified. On `pull_request` events `github.sha` is GitHub's synthetic merge commit, not the PR head — use `github.event.pull_request.head.sha` if a future helper needs the contributor's revision. |

## Condition mapping

The ADO pipeline has no `condition:` expressions and no `dependsOn`; the GHA workflow has no `if:`
expressions. Nothing to translate.

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| Artifactory / `publish_artifact.py` | not used | not used (no push-only guard needed) |
| D2 / `notify_release_orchestrator.py` | not used | not used |
| Compliance attestation | not used | not used |
| Test results | `go test -v` to console only (no `PublishTestResults@2`) | same — console only |
| Build artifact | `ops-control-plane-binary` (Azure Pipelines artifact) | `ops-control-plane-binary` (Actions artifact) |
| Variable groups `shared-ci-secrets` (VG 201), `ops-infra-credentials` (VG 211) | **linked to definition 109 but not referenced** by any step (`NUGET_*`, `NPM_*`, `PIP_INDEX_URL`, `K8S_*`) | not wired. If a deploy step is added later, expose `K8S_SERVICE_ACCOUNT_TOKEN` via `${{ secrets.K8S_SERVICE_ACCOUNT_TOKEN }}` and `K8S_CLUSTER_URL` / `K8S_NAMESPACE` as repository variables. |
| `ContainerRegistry-ACR` service connection (`contosofinancial.azurecr.io`) | **authorised for definition 109 but no `Docker@2` / `docker` step exists** in the YAML | not wired. If image publishing is added later, use `docker/login-action@v3` with `registry: contosofinancial.azurecr.io`, `username: ${{ secrets.ACR_USERNAME }}`, `password: ${{ secrets.ACR_PASSWORD }}`, guarded with `if: github.event_name == 'push'`. |

## Known gaps / behavioural differences

1. **`pull_request` trigger added** (not in ADO). The build job has no side effects beyond an
   Actions artifact, so this is safe.
2. **Coverage profile** is generated but not published in either system (pre-existing ADO gap,
   preserved).
3. **No test-results tab**: GHA has no native equivalent of the ADO Tests tab; the ADO pipeline
   did not use it either, so no behaviour is lost.
4. **Retention**: ADO retention rule was 30 days / min 5 builds. Actions artifacts use the
   repository default (90 days) unless `retention-days` is set.
5. **R6 / R12 are metadata-only**: the variable groups and ACR service connection are bound to
   the ADO definition but unused by the YAML; the GHA workflow reproduces the YAML, not the
   dormant bindings. Recorded above so they are not lost when the ADO definition is retired.
6. **Workflow triggers on changes to itself** (`.github/workflows/ops-control-plane-ci.yml` in
   both `paths` filters). Intentional addition so workflow-only edits get a real build run.
7. **Migration validator baselines**: `validation/baselines/ops-control-plane/` holds values
   observed from ADO build 32 (1 artifact file `ops-control-plane`, 2.36–9.43 MB; 7 `go test`
   cases). The `validate-migration` scorecard passes 7/7 against them.

## Secrets required

None. The workflow reads no `${{ secrets.* }}` values because the ADO YAML consumes none of its
linked variable-group secrets. See the integration table for the secrets to add if deploy/ACR
steps are introduced.
