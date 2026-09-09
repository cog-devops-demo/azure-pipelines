# portfolio-api-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `portfolio-api-ci` (ADO ID **102**) |
| ADO YAML | `services/portfolio-api/azure-pipelines.yml` |
| Category | 1 — central template consumer |
| Template repo / ref | `shared-ci-platform` @ **`master`** (legacy ref; master branch deleted) |
| Templates consumed | `templates/build/build-java.yml`, `templates/release/release-standard.yml` |
| Pool | `ubuntu-latest` (hosted) → `runs-on: ubuntu-latest` |
| Owner | team-quant |
| GHA workflow | `.github/workflows/portfolio-api-ci.yml` |

Templates were expanded manually from their versions on `main`. The ADO MCP server
fails to start in this environment, so `pipeline_get_pipeline` and
`pipeline_preview_pipeline_yaml` could not be used. The documented `master` drift
is applied where it changes the migration: `mavenGoal: package` rather than
`mavenGoals: clean package`, `artifact-registry` rather than `Artifactory`, and
`Notify release-orchestrator` rather than `Notify D2`.

The GitHub `staging` environment must be configured with required reviewers (R5).
The ADO `staging` environment has an approval check requiring at least one
reviewer from `shared-ci-platform-team`, with instructions to verify staging
test results before proceeding.

## 1. Trigger mapping

| ADO | GHA | Note |
|---|---|---|
| `trigger.branches.include: [main, master]` | `on.push.branches: [main, master]` | Both source branches preserved. |
| `trigger.paths.include: [services/portfolio-api/**]` | `on.push.paths` + same list under `on.pull_request.paths` | Exact ADO path filter retained for both events. |
| *(none)* | `on.pull_request.branches: [main, master]` | Added during migration. PR runs build/test/upload only; registration and deploy are push-only. |
| *(none)* | `workflow_dispatch` | Added for manual runs. |
| *(none)* | `concurrency` group per ref, cancel-in-progress on PRs | Added to avoid overlapping PR runs. |

The workflow does not self-trigger on this pull request because the ADO path
filter excludes the workflow file itself. Changes to `.github/workflows/` must
be exercised by a later matching service change or by `workflow_dispatch`.

## 2. Variables

| ADO | GHA (`env:`) | Source |
|---|---|---|
| `variables.artifactName: portfolio-api-dist` | `ARTIFACT_NAME: portfolio-api-dist` | Pipeline |
| `parameters.jdkVersion: '17'` | `JDK_VERSION: '17'` | Pipeline → template |
| `parameters.mavenGoal: 'package'` | `MAVEN_GOAL: package` | Pipeline → documented master template drift |
| `parameters.mavenOptions` (default `-B -DskipTests=false`) | `MAVEN_OPTIONS: -B -DskipTests=false` | Template default |
| `parameters.runTests` / `publishArtifacts` (default `true`) | Steps always present | Template defaults |
| `parameters.environment: staging` | Literal `staging` in deploy job | Pipeline |
| `deployStrategy` (default `rolling`) | Literal `rolling` in deploy step | Template default |
| `requireApproval` (default `false`) | No branch condition; GitHub environment reviewers provide R5 protection | Template default / environment configuration |
| `notifyReleaseOrchestrator` (default `true`) | Notify step present | Template default |
| `mavenPomFile: pom.xml` | `working-directory: services/portfolio-api` + `mvn -f pom.xml` | See known gap G1 |

## 3. Stage → job mapping

| ADO stage | ADO job | GHA job | `needs` | `if` | `environment` |
|---|---|---|---|---|---|
| `Build` — "Build portfolio-api" | `build` (steps from `build-java.yml`) | `build` — "Build portfolio-api" | — | — | — |
| `Release` — "Release to staging" → `Deploy_staging` — "Deploy to staging" | `deployment: deploy` (`runOnce`) | `deploy-staging` — "Deploy to staging" | `build` | `github.event_name == 'push'` | `staging` |

## 4. Step / task mapping

### Build job (`templates/build/build-java.yml`)

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 1 | Implicit checkout | `actions/checkout@v4` | Explicit first step in the job. |
| 2 | `JavaToolInstaller@0` versionSpec=17, x64, PreInstalled | `actions/setup-java@v4` distribution=temurin, java-version=17, `cache: maven` | Hosted agents' pre-installed JDK is represented by Temurin 17. |
| 3 | `Maven@4` mavenPomFile=pom.xml, goals=package, options=`-B -DskipTests=false` | `mvn -f pom.xml $MAVEN_OPTIONS $MAVEN_GOAL` in `services/portfolio-api` | Same goal/options; see G1 for the working directory. |
| 4 | `Maven@4` publishJUnitResults=true, testResultsFiles=`**/surefire-reports/TEST-*.xml` | `Collect JUnit test results` (`find … -path '*/surefire-reports/TEST-*.xml'`, `if: always()`) + `actions/upload-artifact@v4` (`if: always()`) | `find` replaces the ADO glob. Results are retained when tests fail. |
| 5 | `script` "Stage build artifacts" (`cp target/*.jar\|*.war $(Build.ArtifactStagingDirectory)/`) | Same copies into `${{ runner.temp }}/staging` after `mkdir -p` | Runner temp replaces the ADO staging directory. |
| 6 | `PublishBuildArtifacts@1` pathToPublish=staging dir, artifactName=`portfolio-api-dist` | `actions/upload-artifact@v4` name=`portfolio-api-dist` | `if-no-files-found: error` makes an empty distribution fail the build. |
| 7 | `script` "Register artifact in artifact-registry" → `publish_artifact.py --registry artifact-registry` | Same display name and registry argument, push-only | R6 credentials are passed from GitHub secrets. |

### Deploy job (`templates/release/release-standard.yml`)

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 1 | Deployment job starts without checkout | `actions/checkout@v4` | Needed so helper scripts exist on the fresh runner. |
| 2 | `download: current, artifact: portfolio-api-dist` | Prepare `${{ runner.temp }}/staging`, then `actions/download-artifact@v4` | Download path is created before the action writes to it. |
| 3 | `script` "Execute deployment" (echo placeholder) | `Execute deployment` | Same placeholder behavior; no real deployment mechanism exists. |
| 4 | `script` "Notify release-orchestrator" | `Notify release-orchestrator` | `PIPELINE_URL` points to the GitHub Actions run. |
| 5 | `script` "Generate compliance attestation" | `Generate compliance attestation` | Attestation directory is created before the script writes to it. R6 credentials are passed from GitHub secrets. |
| 6 | No explicit retention step | `actions/upload-artifact@v4` `portfolio-api-staging-attestation` | Retains the attestation with the GitHub run. |

Every workflow step has a `mapped from` comment. Test-result collection and
upload use `if: always()`. Registration and deployment are guarded by
`github.event_name == 'push'`.

## 5. Condition mapping

| ADO | GHA | Note |
|---|---|---|
| `Release.dependsOn: Build` | `deploy-staging.needs: build` | |
| `Deploy_staging` has no template condition (`requireApproval=false`) | `if: github.event_name == 'push'` | The guard excludes the added PR and manual runs from deployment. |
| `publishArtifacts=true` | Artifact staging/upload steps present | Template default. |
| `notifyReleaseOrchestrator=true` | Notify step present | Template default. |
| ADO staging approval check | GitHub `environment: staging` with required reviewers | Configure at least one required reviewer, matching R5. |

## 6. ADO variable → GHA shim reference

| ADO env var read by scripts | GHA value |
|---|---|
| `BUILD_SOURCEBRANCH` | `${{ github.ref }}` |
| `BUILD_SOURCEVERSION` | `${{ github.sha }}` |
| `BUILD_BUILDID` (`--build-id`) | `${{ github.run_id }}` |
| `BUILD_ARTIFACTSTAGINGDIRECTORY` | `${{ runner.temp }}/staging` (build) / `${{ runner.temp }}/attestation` (deploy) |
| `BUILD_SOURCESDIRECTORY` | `${{ github.workspace }}` (implicit working directory) |
| `AGENT_NAME` | `${{ runner.name }}` |
| `AGENT_OS` | `${{ runner.os }}` |
| `BUILD_REQUESTEDFOR` | `${{ github.actor }}` |
| `BUILD_DEFINITIONNAME` | `${{ github.workflow }}` |
| `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` + `SYSTEM_TEAMPROJECT` + `/_build/results?buildId=` | `PIPELINE_URL=${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` |

`notify_release_orchestrator.py` prefers `PIPELINE_URL` when set and otherwise
builds the original ADO URL, so existing ADO callers remain compatible.

## 7. Variable groups → GitHub secrets/configuration (R6)

The exact variable names below come from `docs/samples/ado-api-responses.json`.
Only values needed by the current helper scripts are wired into workflow steps;
the helper scripts currently write local manifests rather than making external
registry or compliance-store calls.

| ADO group | Exact variables | GitHub configuration | Workflow use |
|---|---|---|---|
| VG 201 `shared-ci-secrets` | `NUGET_FEED_URL`, `NUGET_API_KEY`, `PIP_INDEX_URL`, `NPM_REGISTRY`, `NPM_TOKEN` | Repository or organization secrets/config as appropriate | Not consumed by this Java workflow; retain names for future shared-tool use. |
| VG 205 `artifact-registry-credentials` | `ARTIFACT_REGISTRY_URL`, `ARTIFACT_REGISTRY_TOKEN` | Repository or environment secrets | `Register artifact in artifact-registry` step. |
| VG 206 `compliance-store-credentials` | `COMPLIANCE_STORE_URL`, `COMPLIANCE_STORE_TOKEN`, `COMPLIANCE_STORE_CERT_THUMBPRINT` | Repository or `staging` environment secrets | URL and token are passed to attestation; certificate thumbprint is not consumed by the current stub. |

## 8. Integration points

| System | ADO | GHA | Handling |
|---|---|---|---|
| **artifact-registry** | `publish_artifact.py --registry artifact-registry` | Same registry argument, push-only | VG 205 URL/token are passed as secrets; the current script writes a manifest locally. |
| **release-orchestrator** | `notify_release_orchestrator.py` | Same script with `PIPELINE_URL` | Script prefers the GitHub URL and retains the ADO fallback. |
| **compliance-store** | `generate_attestation.py` | Same script, with VG 206 URL/token env vars | Current script writes an attestation locally; certificate-thumbprint auth needs a future design. |
| Azure (`AzureSubscription-Staging`) | Bound to the ADO project | Not configured | Deploy is an echo placeholder; add OIDC federation when a real deploy exists. |
| Test results | `Maven@4 publishJUnitResults` → ADO Tests tab | Artifact `portfolio-api-test-results` | GitHub Actions has no native equivalent in this workflow. |

## 9. Known gaps / behavioural differences

| ID | Gap | Impact / decision |
|---|---|---|
| **G1** | The repository has no `pom.xml` at the root, and no `pom.xml` in `services/portfolio-api` on `main`, although the ADO template's `mavenPomFile: pom.xml` implies one. | The workflow runs `mvn -f pom.xml` in `services/portfolio-api`, preserving the service-oriented migration layout. Confirm the real service checkout before cut-over. |
| **G2** | `master` `build-java.yml` used `mavenGoal: package`; `main` uses `mavenGoals: clean package`. | Workflow keeps the documented master behavior (`package`, no `clean`). |
| **G3** | The ADO template reference points to deleted `master`; template expansion therefore uses `main` plus documented master drift. | Master-faithful display names and registry argument are retained in the workflow. |
| **G4** | ADO Tests tab results are represented by a GitHub artifact. | Consumers must download `portfolio-api-test-results` to inspect XML. |
| **G5** | ADO ran only on push; GHA also runs build/test on pull requests and `workflow_dispatch`. | Registration and deployment remain push-only. |
| **G6** | The workflow path filter intentionally remains exactly `services/portfolio-api/**`. | The workflow does not self-trigger on this PR because its own path is outside that filter. Use a matching service change or `workflow_dispatch` to exercise it. |

## 10. Required GitHub configuration

| Item | Required | Notes |
|---|---|---|
| GitHub environment `staging` | **Yes** | Add required reviewers; mirror the ADO approval check for `shared-ci-platform-team`, minimum one reviewer (R5). |
| `ARTIFACT_REGISTRY_URL` | **Yes for real registry integration** | VG 205; passed to the register step. |
| `ARTIFACT_REGISTRY_TOKEN` | **Yes for real registry integration** | VG 205 secret; passed to the register step. |
| `COMPLIANCE_STORE_URL` | **Yes for real compliance-store integration** | VG 206; passed to the attestation step. |
| `COMPLIANCE_STORE_TOKEN` | **Yes for real compliance-store integration** | VG 206 secret; passed to the attestation step. |
| `COMPLIANCE_STORE_CERT_THUMBPRINT` | **Not consumed currently** | VG 206 secret; certificate-based auth needs a future hosted-runner/OIDC design. |
| Azure OIDC federation for `staging` | **Not yet** | Needed only when the placeholder deployment becomes real. |

## 11. Files in this migration

- `.github/workflows/portfolio-api-ci.yml` — new workflow
- `docs/migration/portfolio-api-ci-ado-to-gha-mapping.md` — this mapping
- `build-tools/scripts/notify_release_orchestrator.py` — `PIPELINE_URL` support with the ADO fallback

ADO YAML under `services/` and `templates/` is unchanged. No validation files
were added.
