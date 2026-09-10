# Portfolio API canary: ADO-to-GHA mapping

## Overview

| Field | ADO value | GHA mapping |
|---|---|---|
| Pipeline | `services/portfolio-api/azure-pipelines-canary.yml` | `.github/workflows/portfolio-api-canary.yml` |
| ADO ID | 103 | `portfolio-api-canary` workflow |
| Category | Category 1 | Workflow-dispatch smoke test |
| Stack | Java 17 / Maven | `actions/setup-java@v4` and Maven |
| Owner | `team-quant` | Same owner |
| Last run | 2026-02-28 | Not applicable until dispatched |
| Runs in the last 90 days | 5 | Not applicable until dispatched |

The ADO pipeline is a manual-only canary used to exercise the shared Java build
template against the `portfolio-api` service. The GHA workflow preserves the
manual dispatch behavior, adds a scoped pull-request validation trigger, and
inlines the locally available `main` template variant.

## Trigger mapping

| ADO configuration | GHA configuration | Notes |
|---|---|---|
| `trigger: none` | `on: workflow_dispatch` | Preserves the manual invocation mode. |
| No ADO equivalent | `on: pull_request` with `branches: [main]` and `paths: ['services/portfolio-api/**']` | Intentional GHA addition for pull-request validation limited to portfolio API changes. |
| `parameters.templateBranch` | `workflow_dispatch.inputs.templateBranch` | A choice input with `main`, `master`, `staging/preprod`, and `staging/release-hardening`; default is `main`. |

The source pipeline is manual-only. The pull-request trigger is an intentional
GHA addition for validation of changes under `services/portfolio-api/**` on
the `main` branch. Registration remains deliberately guarded to
`workflow_dispatch`, so pull-request builds do not register artifacts.

## Template resolution

The ADO pipeline selects one of four repository resources at queue time. The
GHA workflow runs the `main` template logic inlined from
`templates/build/build-java.yml` and reports an annotation when another branch
is requested.

| Requested template branch | Available locally? | GHA behavior |
|---|---|---|
| `main` | Yes | Runs the inlined `main` variant. |
| `master` | No | Not in repo, not verifiable; runs the `main` variant and emits a warning. |
| `staging/preprod` | No | Not in repo, not verifiable; runs the `main` variant and emits a warning. |
| `staging/release-hardening` | No | Not in repo, not verifiable; runs the `main` variant and emits a warning. |

The available local branches were checked with `git branch -a`; only `main`
exists locally. The other template branches therefore cannot be expanded or
compared from this repository.

## Stage/job mapping

| ADO stage/job | GHA job | Mapping |
|---|---|---|
| Stage `Build` (`Build portfolio-api (canary - <templateBranch>)`) | Job `build` (`Build portfolio-api (canary - ${{ inputs.templateBranch }})`) | One GHA job retains the stage and job display context. |
| Job `build` | `jobs.build` on `ubuntu-latest` | Uses the same Ubuntu runner family and executes the template steps in order. |

## Task mapping

| ADO task or step | GHA step | Input translation |
|---|---|---|
| Implicit `checkout: self` | `Checkout` using `actions/checkout@v4` | Checks out the repository into the workspace. |
| `JavaToolInstaller@0` (`versionSpec: 17`, `jdkArchitectureOption: x64`, `jdkSourceOption: PreInstalled`) | `Install JDK 17` using `actions/setup-java@v4` | `java-version: 17`, `architecture: x64`, Temurin distribution; Maven cache is intentionally enabled. |
| `Maven@4` (`mavenPomFile: services/portfolio-api/pom.xml`) | `Maven clean package` | `mvn -f "$PROJECT_DIR/pom.xml" -B -DskipTests=false clean package`; runs tests. |
| `Maven@4` (`publishJUnitResults: true`, `testResultsFiles: **/surefire-reports/TEST-*.xml`) | `Collect JUnit test results` and `Upload test results` | Uses `find` to collect `*/surefire-reports/TEST-*.xml`, then uploads the files as an artifact because GHA has no native test-results tab equivalent here. |
| Template script `Stage build artifacts` | `Stage build artifacts` | Creates the staging directory, then copies `target/*.jar` and `target/*.war`; missing file types are tolerated as in ADO. |
| `PublishBuildArtifacts@1` (`pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: $(artifactName)`) | `Upload artifacts` using `actions/upload-artifact@v4` | Uploads `runner.temp/staging` as `portfolio-api-canary`. |
| Template script `Register artifact in Artifactory` | `Register artifact in Artifactory` | Runs `publish_artifact.py --name "$ARTIFACT_NAME" --registry Artifactory --build-id "$BUILD_BUILDID"` under the manual-dispatch guard. |
| Stage display name | `Write canary run summary` | Writes the requested and executed template branches and build settings to the GHA step summary. |

The step comments in `.github/workflows/portfolio-api-canary.yml` use
`# --- mapped from:` markers corresponding to the ADO tasks and source
configuration above.

## Variable mapping

| ADO variable or parameter | GHA equivalent | Use |
|---|---|---|
| `$(artifactName)` | `ARTIFACT_NAME=portfolio-api-canary` | Artifact upload and registration name. |
| `templates_branch` / `${{ parameters.templateBranch }}` | `TEMPLATES_BRANCH=${{ inputs.templateBranch }}` | Requested template branch, used by branch resolution and the summary. |
| `parameters.jdkVersion` | `JDK_VERSION=17` | Java setup input. |
| `parameters.projectDirectory` | `PROJECT_DIR=services/portfolio-api` | Maven project location. |
| `parameters.mavenGoals` | `MAVEN_GOALS=clean package` | Template default Maven goals. |
| `parameters.mavenOptions` | `MAVEN_OPTIONS=-B -DskipTests=false` | Template default Maven options. |
| `parameters.runTests` | Maven execution plus result collection | The template default is `true`; the workflow runs tests and collects Surefire XML. |
| `parameters.publishArtifacts` | Artifact staging and upload steps | The template default is `true`; the workflow publishes the canary artifact. |
| `$(Build.ArtifactStagingDirectory)` | `${{ runner.temp }}/staging` / `$RUNNER_TEMP/staging` | Temporary artifact staging directory; created with `mkdir -p` before writes. |
| `$(Build.BuildId)` | `github.run_id` via `BUILD_BUILDID` | Build identifier passed to `publish_artifact.py`. |
| `$(Build.SourcesDirectory)` | `GITHUB_WORKSPACE` | Helper-script path: `$GITHUB_WORKSPACE/build-tools/scripts/publish_artifact.py`. |
| `BUILD_SOURCEBRANCH` | `${{ github.ref }}` | Environment shim for the helper manifest. |
| `BUILD_SOURCEVERSION` | `${{ github.sha }}` | Environment shim for the helper manifest. |
| `AGENT_NAME` | `${{ runner.name }}` | Environment shim for the helper manifest. |
| `BUILD_ARTIFACTSTAGINGDIRECTORY` | `${{ runner.temp }}/staging` | Environment shim controlling the helper manifest destination. |
| Pipeline URL metadata | `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` | GHA run URL shim for registration metadata and future helper compatibility. |

## Condition mapping

| ADO condition | GHA mapping | Result |
|---|---|---|
| Compile-time `${{ if eq(parameters.templateBranch, 'main') }}` and the three equivalent branch conditions | Runtime `Resolve template branch` step | Logs the requested branch; non-`main` requests emit a `::warning` annotation and execute the inlined `main` template variant. |
| `trigger: none` | `on: workflow_dispatch` | Manual invocation only. |
| No ADO pull-request trigger | `on: pull_request` for `main` and `services/portfolio-api/**` | Intentional GHA validation addition. |
| ADO manual execution behavior | `if: github.event_name == 'workflow_dispatch'` on registration | Keeps Artifactory registration limited to the original manual execution mode, even if another trigger is added later. |

## Integration points

| Integration | Mapping |
|---|---|
| Artifactory registration | Kept. The workflow invokes `build-tools/scripts/publish_artifact.py` after staging and uploading the artifact. The helper writes a local manifest; it does not call an external Artifactory API. |
| D2 / attestation | Not present in the ADO source pipeline; not applicable to this migration. |

## Helper scripts

No helper-script changes were made. `publish_artifact.py` reads
`BUILD_SOURCEBRANCH`, `BUILD_SOURCEVERSION`, `AGENT_NAME`, and
`BUILD_ARTIFACTSTAGINGDIRECTORY`, all of which are supplied by the workflow's
environment shims. It does not construct ADO URLs, so no helper change is
needed; the workflow supplies `PIPELINE_URL` as a compatible run-URL shim.

## Known gaps

- Only the `main` template branch is available locally. The `master`,
  `staging/preprod`, and `staging/release-hardening` variants could not be
  verified; those choices run the inlined `main` variant and emit a warning.
- GHA does not provide the ADO native test-results tab in this mapping. Surefire
  XML files are uploaded as a `test-results-portfolio-api-canary` artifact
  instead.
- The baseline artifact name is `portfolio-api-dist`; this canary intentionally
  publishes `portfolio-api-canary`, matching ADO pipeline 103.
- The workflow uses `find` rather than a recursive `**` glob for portable
  result collection, and creates staging directories with `mkdir -p` before
  writing files.
- `actions/setup-java` adds `cache: maven` intentionally; this is an
  optimization in the GHA implementation and does not alter the build inputs.

## Secrets required

None. `publish_artifact.py` writes a local manifest under the staging
directory and does not require credentials or make a network registration
request.

## Retirement note

Retire this workflow once the template branches are consolidated onto `main`.
At that point, the branch-choice input and warning path can be removed, or the
workflow can be replaced by the canonical portfolio API build workflow.

## ADO MCP verification result

The available ADO MCP server points to a different ADO organization. Its
projects are `ado_org` and `shawn`; `danagajewski-demo` does not exist there.
Consequently, pipeline 103 and the other template branches could not be
verified through ADO MCP. This mapping uses the supplied ADO source and a
manual expansion of the locally available `main` template.
