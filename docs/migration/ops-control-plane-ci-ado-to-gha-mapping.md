# ops-control-plane-ci migration mapping

| Field | Value |
| --- | --- |
| Pipeline | `ops-control-plane-ci` |
| ADO ID | 109 (live definition id 3 in `danagajewski/danagajewski-demo`) |
| Category | 4 custom inline |
| Owner | platform-team |
| Stack | Go 1.22 |
| Source YAML | `services/ops-control-plane/azure-pipelines.yml` |
| Workflow | `.github/workflows/ops-control-plane-ci.yml` |

## Trigger mapping

| ADO | GHA |
| --- | --- |
| `push` branches include `main`, paths include `services/ops-control-plane/**` | `push` branches `main`, paths `services/ops-control-plane/**` and `.github/workflows/ops-control-plane-ci.yml` |
| No ADO equivalent for workflow-file path | The workflow file is intentionally added to the push path filter so workflow changes validate themselves |
| Live ADO definition has a PR trigger on `main` with empty `pathFilters` (builds every PR) | `pull_request` on `main` is intentionally added for earlier CI feedback, but is path-filtered to the service and workflow file |
| No ADO equivalent | `workflow_dispatch` is intentionally added as the equivalent of the ADO “Run pipeline” button |

The GHA pull request trigger is path-filtered whereas the live ADO PR trigger has empty
`pathFilters`; this difference is intentional.

## Stage and job mapping

| ADO stage/job | GHA job |
| --- | --- |
| Stage `Build ops-control-plane` / job `build_go` (`Go build and test`) | Job `build`, named `Build ops-control-plane`, on `ubuntu-latest`, with `defaults.run.working-directory: services/ops-control-plane` |

| GHA step | ADO step |
| --- | --- |
| `Checkout` (`actions/checkout@v4`) | Implicit ADO checkout |
| `Install Go 1.22` (`actions/setup-go@v5`) | `GoTool@0` version 1.22 |
| `Download modules` | Script `Download modules`: `go mod download`; `go mod verify` |
| `Vet` | Script `Vet`: `go vet ./...` |
| `Run tests` | Script `Run tests`: `go test ./... -v -coverprofile=coverage.out` |
| `Build binary` | Script `Build binary`: `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o $(Build.ArtifactStagingDirectory)/ops-control-plane ./cmd/server` |
| `Publish binary` | `PublishBuildArtifacts@1`: path `$(Build.ArtifactStagingDirectory)`, artifact name `ops-control-plane-binary` |

## Task mapping

| ADO task | GHA task |
| --- | --- |
| `GoTool@0` version 1.22 | `actions/setup-go@v5` with `go-version: '1.22'` and `cache: false`; ADO had no module cache |
| `PublishBuildArtifacts@1` | `actions/upload-artifact@v4` with the same artifact name, `ops-control-plane-binary`, and `if-no-files-found: error` |
| Inline scripts | `run` steps; the job default supplies `working-directory: services/ops-control-plane` |

## Variable mapping

| ADO variable | GHA variable |
| --- | --- |
| `GOPATH=$(system.defaultWorkingDirectory)/go` | `GOPATH=${{ github.workspace }}/go` |
| `GOBIN=$(GOPATH)/bin` | `GOBIN=${{ github.workspace }}/go/bin` |
| `modulePath` | `MODULE_PATH=services/ops-control-plane` |
| `$(Build.ArtifactStagingDirectory)` | `STAGING_DIR=${{ github.workspace }}/staging`; `Build binary` creates it with `mkdir -p` |
| ADO predefined variables | `BUILD_SOURCEBRANCH=${{ github.ref }}`, `BUILD_SOURCEVERSION=${{ github.sha }}`, `BUILD_BUILDID=${{ github.run_id }}`, and `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` |

The predefined-variable shims are retained for parity with other migrated workflows; no
script consumes them here.

## Condition mapping

There are no conditions in ADO (no conditional steps or jobs and no deploy stage), so no
conditions were added to GHA.

## Integration points

| Integration point | Mapping |
| --- | --- |
| Artifactory | Not present in the ADO YAML; not added |
| D2 | Not present in the ADO YAML; not added |
| Attestation | Not present in the ADO YAML; not added |
| Test results | ADO runs `go test` but publishes no test results (zero ADO test runs); GHA runs the same command and publishes none |
| Helper scripts | None called; `build-tools/scripts` is unchanged |

## Unused ADO bindings

The variable group `ops-infra-credentials` (K8s token) and service connection
`ContainerRegistry-ACR` are attached to ADO definition 109, but no YAML step uses them.
No deploy was invented. Platform-team should confirm they are unused and remove them from
the ADO definition before retirement. If image publishing is later needed, add a
`docker/login-action@v3` step using `${{ secrets.* }}` at that time.

## Known gaps

1. `coverage.out` is produced but never published, the same as ADO; this behavior is preserved.
2. No test report is published, so the parity report’s “Tests run” row shows “not measured”
   (EXCEPTION, not a mismatch). Publishing JUnit in GHA would mismatch ADO’s zero recorded tests.
3. `BUILD_SOURCEVERSION` on `pull_request` is the merge commit SHA.
4. The GHA `pull_request` trigger is path-filtered, whereas the live ADO PR trigger is not.

## Secrets required

None.

## Verification performed

### Go 1.22 build and test

Ran:

```text
cd services/ops-control-plane && go vet ./... && go test ./... -v -coverprofile=coverage.out && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /tmp/ocp/ops-control-plane ./cmd/server && ls -l /tmp/ocp
```

Go 1.22.12 was installed for the check. `go vet ./...` passed, and `go test ./... -v
-coverprofile=coverage.out` passed with 7 tests: 1 top-level test function and 6 subtests.
The binary build passed and `coverage.out` was removed afterward.

```text
go version go1.22.12 linux/amd64
PASS
coverage: 100.0% of statements
ok  	github.com/contoso-financial/ops-control-plane/internal/controls	0.001s	coverage: 100.0% of statements
total 4828
-rwxr-xr-x 1 ubuntu ubuntu 4939928 Sep 10 13:37 ops-control-plane
```

The binary size was 4,939,928 bytes (about 4.9 MB).

### actionlint

Ran `actionlint -version && actionlint .github/workflows/ops-control-plane-ci.yml`.
actionlint 1.7.7 completed cleanly with no diagnostics.

### Migration validator

Ran:

```text
python3 validation/scripts/validate_migration.py --service ops-control-plane --ado-pipeline services/ops-control-plane/azure-pipelines.yml --gha-workflow .github/workflows/ops-control-plane-ci.yml --baselines validation/baselines --repo-root "$PWD"
```

The validator reported 100% (5/5 checks passed), and every row in the Validation
Scorecard was PASS:

| Check | Status | Details |
| --- | --- | --- |
| YAML Syntax | PASS | Valid YAML |
| Trigger Configuration | PASS | Triggers: push, pull_request, workflow_dispatch |
| Stage → Job Mapping | PASS | 1/1 ADO stages mapped to GHA jobs |
| Environment Gates | PASS | No deployment jobs (OK) |
| Integration Points | PASS | Required (from ADO): Test Results; Found: Test Results; Missing: none; Not applicable: Artifactory, D2 Notification, Compliance Attestation |

The validator also reported the stored advisory baselines as PASS: artifact baseline
1 file and test baseline 7 tests (`go-test`).
