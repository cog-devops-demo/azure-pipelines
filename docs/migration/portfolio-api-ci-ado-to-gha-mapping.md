# portfolio-api-ci ADO-to-GitHub Actions mapping

## Overview

| Field | Value |
|---|---|
| Pipeline | `portfolio-api-ci` |
| ADO pipeline ID | `102` |
| Category | `1` |
| Owner | `team-quant` |
| Stack | Java 17 / Maven |
| ADO source | `services/portfolio-api/azure-pipelines.yml` |
| GHA workflow | `.github/workflows/portfolio-api-ci.yml` |

The migration preserves the build, test-result publication, artifact, Artifactory,
deployment, D2 notification, and compliance-attestation behavior represented by
the expanded ADO pipeline.

## Template resolution & the `master` assumption

The ADO pipeline references `shared-ci-platform@master`, but that branch is absent
from this repository. The templates were resolved from `main`. A live ADO preview
retrieved through the REST API for org `danagajewski`, project
`danagajewski-demo`, definition `portfolio-api-ci` (definition ID `4`) confirms
that `master` and `main` have identical template content for this migration.
The ADO MCP server available in this environment points to a different org
(`shawn0864`), so it was not used for the preview. The only observed difference
is the deploy notification step display name: live ADO shows `Notify release-orchestrator`,
while the `main` template shows `Notify D2`.

## Trigger mapping

| ADO | GHA | Equivalence note |
|---|---|---|
| `trigger.branches.include: [main, master]` | `push.branches: [main, master]` | `master` is carried over intentionally; it is a dead branch and inert unless recreated. |
| `trigger.paths.include: services/portfolio-api/**` | `push.paths` with the service path and workflow path | The workflow path is included so workflow edits self-validate. |
| No `pr:` block | `pull_request.paths` with the service path and workflow path | `pull_request` is added for migration validation and PR feedback. |
| Not present | `workflow_dispatch` | Manual execution is available in GHA. |

The release of the ADO `paths` restriction is not broadened to unrelated services:
only portfolio-api changes and this workflow trigger the workflow.

## Stage → job mapping

| ADO stage | GHA job | Runner / environment | Condition |
|---|---|---|---|
| `Build` / `build` | `build` / `Build portfolio-api` | `ubuntu-latest` / none | All supported events |
| `Deploy_staging` / `deploy` | `deploy-staging` / `Deploy to staging` | `ubuntu-latest` / `staging` | Push events only |

## Step-by-step task mapping

| ADO task or expanded step | GHA step | Input translation |
|---|---|---|
| Implicit `checkout: self` in build | `actions/checkout@v4` | Checks out the workflow repository. |
| `JavaToolInstaller@0` | `Install JDK 17` / `actions/setup-java@v4` | `jdkVersion: 17` becomes Temurin 17 with Maven caching. The Temurin distribution is an assumption: ADO hosted Ubuntu's preinstalled JDK 17 is treated as Temurin. |
| `Maven@4` | `Maven package` | Runs `mvn -B -DskipTests=false -f services/portfolio-api/pom.xml package`; publishes JUnit XML separately. |
| `Maven@4` `publishJUnitResults: true` and `testResultsFiles: **/surefire-reports/TEST-*.xml` | `Upload JUnit test results` | Uploads `portfolio-api-test-results`; it runs with `always()` and warns if no files exist. |
| Script `Stage build artifacts` | `Stage build artifacts` | Copies single-level `target/*.jar` and `target/*.war` into the staging directory; each copy keeps `2>/dev/null || true`. |
| `PublishBuildArtifacts@1` | `Upload artifacts` / `actions/upload-artifact@v4` | `$(Build.ArtifactStagingDirectory)` becomes the staging directory and `artifactName` becomes `portfolio-api-dist`. |
| Script `Register artifact in Artifactory` | `Register artifact in Artifactory` | Runs `publish_artifact.py` with `--name portfolio-api-dist`, `--registry Artifactory`, and the GHA run ID as build ID; gated to pushes. |
| `checkout: self` in deployment | `actions/checkout@v4` | Checks out scripts on the fresh deployment runner. |
| `DownloadBuildArtifacts@1` | `Download portfolio-api-dist` / `actions/download-artifact@v4` | Downloads the single artifact into `${{ runner.temp }}/portfolio-api-dist`. |
| Script `Execute deployment` | `Execute deployment` | Echoes the artifact, `staging`, and `rolling` strategy. |
| Script `Notify D2` | `Notify D2` | Calls `notify_release_orchestrator.py`; the script now prefers the GHA `PIPELINE_URL` and retains the ADO fallback. |
| Script `Generate compliance attestation` | `Generate compliance attestation` | Calls `generate_attestation.py`, which writes the attestation under the mapped staging directory. |
| No ADO equivalent | `Upload compliance attestation` | GHA-only retention of `*-attestation.json`; the addition is documented rather than treated as an ADO task. |

## Variable mapping

| ADO variable | GHA value |
|---|---|
| `artifactName` | `ARTIFACT_NAME=portfolio-api-dist` |
| `jdkVersion` | `JDK_VERSION=17` |
| `projectDirectory` | `PROJECT_DIRECTORY=services/portfolio-api` |
| `mavenGoals` | `MAVEN_GOALS=package` |
| `mavenOptions` default | `MAVEN_OPTIONS=-B -DskipTests=false` |
| Release `environment` | `DEPLOY_ENVIRONMENT=staging` and job `environment: staging` |
| `Build.SourceBranch` | `BUILD_SOURCEBRANCH=${{ github.ref }}` |
| `Build.SourceVersion` | `BUILD_SOURCEVERSION=${{ github.sha }}` |
| `Build.BuildId` | `BUILD_BUILDID=${{ github.run_id }}` |
| `Build.DefinitionName` | `BUILD_DEFINITIONNAME=${{ github.workflow }}` |
| `Build.RequestedFor` | `BUILD_REQUESTEDFOR=${{ github.actor }}` |
| `System.TeamFoundationCollectionUri` | `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI=${{ github.server_url }}/` |
| `System.TeamProject` | `SYSTEM_TEAMPROJECT=${{ github.repository }}` |
| GHA run URL | `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` |
| `Build.ArtifactStagingDirectory` | `BUILD_ARTIFACTSTAGINGDIRECTORY=$RUNNER_TEMP/staging`, exported through `GITHUB_ENV` |
| `Agent.Name` | `AGENT_NAME=$RUNNER_NAME`, exported through `GITHUB_ENV` |
| `Agent.OS` | `AGENT_OS=$RUNNER_OS`, exported through `GITHUB_ENV` |

## Condition mapping

ADO has no stage condition in the expanded release template. With
`requireApproval: false`, ADO ran `Deploy_staging` on PR builds as well as other
successful builds. The GHA deployment and Artifactory registration are gated to
push events intentionally: PRs build and publish validation artifacts but do not
deploy or register them. The `staging` GHA environment and its protection rules
replace the ADO environment approver mechanism.

## Integration points

| Integration | GHA behavior |
|---|---|
| Artifactory | `publish_artifact.py` runs on pushes after the `portfolio-api-dist` upload. |
| D2 / release orchestrator | `notify_release_orchestrator.py` runs during staging deployment and uses `PIPELINE_URL` when present, with the existing ADO URL fallback. |
| Compliance attestation | `generate_attestation.py` creates `portfolio-api-dist-attestation.json`; the workflow uploads it as `portfolio-api-staging-attestation`. |
| Tests | Surefire JUnit XML is uploaded as `portfolio-api-test-results`. |

## Known gaps

- GHA has no native test tab in this workflow; JUnit XML is retained as an artifact. `dorny/test-reporter` is an optional future addition.
- Deployment is skipped on PRs in GHA, unlike the observed ADO behavior.
- `master` is a dead branch carried over for trigger parity.
- The `setup-java` Temurin distribution is an assumption about the ADO hosted Ubuntu JDK 17.
- The attestation artifact is a GHA-only retention addition.
- `publish_artifact.py` writes its manifest after the build artifact upload, so the manifest is not in `portfolio-api-dist`; this is the same ordering as ADO.

## Secrets required

No secrets are required: the helper scripts are stubs and no `${{ secrets.* }}`
values are used. The repository must have a `staging` environment configured in
its settings with any desired reviewers or protection rules.

## Validation

`validation/scripts/validate_migration.py` checks YAML syntax, trigger presence,
the two-stage-to-two-job mapping, the `staging` environment, stored baselines,
and required integration-point steps. It is run with the portfolio-api ADO
source and this workflow.

The runtime parity check in `validation/scripts/parity_report.py` compares the
live GHA run for the PR head SHA with the corresponding ADO run. It requires a
successful GHA result, a `portfolio-api-dist` artifact, and a test artifact
containing JUnit XML with exactly five test cases.
