# portfolio-api-canary — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `portfolio-api-canary` (ADO ID **103**; live mirror: pipeline 5 in `danagajewski/danagajewski-demo`) |
| ADO YAML | `services/portfolio-api/azure-pipelines-canary.yml` |
| GHA workflow | `.github/workflows/portfolio-api-canary.yml` |
| Category | 1 — central-template consumer (template test harness) |
| Stack | Java 17 / Maven |
| Pool | `ubuntu-latest` (hosted) → `runs-on: ubuntu-latest` |
| Owner | team-quant (`j.chen@contoso.com`) |
| Trigger | manual only (`trigger: none`) with `templateBranch` parameter |
| Run history (snapshot) | last run 2026-02-28 with `templateBranch=staging/preprod`, succeeded |
| Variable groups | VG 201 `shared-ci-secrets` bound in ADO (R6) — **no expanded step reads any of its variables** |
| Risk flags | R3 multi-branch template fan-out; R6 variable group |

> **This workflow is transitional.** Pipeline 103 exists only to A/B `templates/build/build-java.yml`
> across four template branches. Once `master`, `staging/preprod` and `staging/release-hardening`
> are unified onto `main` (or onto a reusable Java workflow), the branch selector has a single value
> and this workflow duplicates `portfolio-api-ci`. Retire it at that point.

## 1. Template resolution (all four branches)

The ADO file declares four repository resources (`templates_main`, `templates_master`,
`templates_preprod`, `templates_hardened`) and uses compile-time
`${{ if eq(parameters.templateBranch, '<branch>') }}` blocks so exactly one
`templates/build/build-java.yml@<alias>` expands per run, always with `jdkVersion: '17'` and
`artifactName: $(artifactName)` (= `portfolio-api-canary`). No goals parameter is passed, so each
branch's default applies.

The four variants were read from the `shared-ci-platform` repo in the ADO org (the template
branches are not present on this GitHub mirror; `main` here is byte-identical to ADO `main`).
The `main` variant was also confirmed via the ADO preview API (`pipelines/5/preview`, with
`templateBranch=staging/preprod`), which returned the expanded steps listed below.

| Aspect | `main` | `master` | `staging/preprod` | `staging/release-hardening` |
|---|---|---|---|---|
| Goals parameter | `mavenGoals` = **`clean package`** | `mavenGoal` = **`package`** | `mavenGoal` = `package` | `mavenGoal` = `package` |
| Extra parameter | — | `projectDirectory` (default `.`) | — | — |
| `Maven@4.mavenPomFile` | `pom.xml` | `${{ parameters.projectDirectory }}/pom.xml` → `./pom.xml` | `pom.xml` | `pom.xml` |
| Stage-artifacts script | `cp target/*.jar …` | `cp ./target/*.jar …` | `cp target/*.jar …` | `cp target/*.jar …` |
| `publish_artifact.py --registry` | **`Artifactory`** | `artifact-registry` | `artifact-registry` | `artifact-registry` |
| Register step displayName | `Register artifact in Artifactory` | `Register artifact in artifact-registry` | same | same |
| `JavaToolInstaller@0`, `mavenOptions -B -DskipTests=false`, `publishJUnitResults: true`, `testResultsFiles '**/surefire-reports/TEST-*.xml'`, `PublishBuildArtifacts@1` | identical | identical | identical | identical |

`staging/preprod` and `staging/release-hardening` are byte-identical to each other. The
`build-tools/scripts/publish_artifact.py` copies on the three non-`main` branches differ from `main`
only in docstring/comment wording. The script runs from the **consuming** checkout
(`$(Build.SourcesDirectory)`), i.e. this repo's `main` copy, regardless of template branch — the
GHA workflow does the same.

### Resolved step list (source of truth for the workflow)

| # | `main` | `master` | `staging/preprod` / `staging/release-hardening` |
|---|---|---|---|
| 1 | `JavaToolInstaller@0` 17 / x64 / PreInstalled | same | same |
| 2 | `Maven@4` `pom.xml`, `clean package`, `-B -DskipTests=false`, JUnit `**/surefire-reports/TEST-*.xml` | `./pom.xml`, `package` | `pom.xml`, `package` |
| 3 | script: `cp target/*.{jar,war} $(Build.ArtifactStagingDirectory)/ 2>/dev/null \|\| true` | `cp ./target/*.{jar,war} …` | same as `main` |
| 4 | `PublishBuildArtifacts@1` → `portfolio-api-canary` | same | same |
| 5 | `python $(Build.SourcesDirectory)/build-tools/scripts/publish_artifact.py --name portfolio-api-canary --registry Artifactory --build-id $(Build.BuildId)` | `--registry artifact-registry` | `--registry artifact-registry` |

`build-java.yml` has **no** D2 notification and **no** compliance attestation step on any branch;
those live in `templates/release/*.yml`, which the canary never references.

## 2. Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger: none` | no `push` trigger | 1:1 |
| `parameters.templateBranch` (string, default `main`, values `main` / `master` / `staging/preprod` / `staging/release-hardening`) | `on.workflow_dispatch.inputs.template_branch` (`type: choice`, same default and values, **plus `all`**) | `all` fans out to a 4-way matrix — the canary's purpose (compare branches) in one run. **Intentional addition.** |
| — | `on.pull_request` (`branches: [main]`, `paths: services/portfolio-api/**, templates/build/build-java.yml`) | **Intentional addition** per migration policy. PR runs resolve to the `main` variant only (`inputs` is empty) and never register artifacts. |
| VG 201 `shared-ci-secrets` | not mapped | No expanded step reads it; nothing to configure. |

## 3. Stage / job mapping

| ADO stage → job | GHA job | `needs` | Strategy |
|---|---|---|---|
| `Build` (`Build portfolio-api (canary - ${{ parameters.templateBranch }})`) → `build` | `build` (`Build portfolio-api (canary - ${{ matrix.template_branch }})`) | — | `matrix.template_branch` = `[<selected>]`, or all four when `all` is chosen; `fail-fast: false` so one branch's failure doesn't cancel the comparison |

The ADO compile-time `${{ if eq(parameters.templateBranch, …) }}` selector becomes step-level
`if: matrix.template_branch == '<branch>'` guards. Steps that are textually identical across
branches (JDK, upload, test collection) are shared; steps that differ are inlined once per variant.

## 4. Task / step mapping

| # | ADO task / step | GHA step | Translation notes |
|---|---|---|---|
| 0 | implicit `checkout: self` | `actions/checkout@v4` | |
| 1 | `JavaToolInstaller@0` (17, x64, PreInstalled) | `actions/setup-java@v4` `distribution: temurin`, `java-version: 17`, `architecture: x64` | Hosted ADO images preinstall Temurin; no Maven cache (ADO had none). |
| 2 | `Maven@4` @ `main` | `Maven clean package`: `mvn -f pom.xml $MAVEN_OPTIONS clean package` (`if: == 'main'`) | |
| 2 | `Maven@4` @ `master` | `Maven package`: `mvn -f ./pom.xml $MAVEN_OPTIONS package` (`if: == 'master'`) | `projectDirectory` default `.` resolved. |
| 2 | `Maven@4` @ `staging/preprod` | `Maven package (staging/preprod)`: `mvn -f pom.xml $MAVEN_OPTIONS package` | |
| 2 | `Maven@4` @ `staging/release-hardening` | `Maven package (staging/release-hardening)`: same command | |
| 2b | `Maven@4.publishJUnitResults` + `**/surefire-reports/TEST-*.xml` | `Collect JUnit test results` (`find … -path '*/surefire-reports/TEST-*.xml'` + `cp --parents`) → `actions/upload-artifact@v4` `test-results-<variant>` (`if: always()`) | `find` replaces `**` (no globstar in GHA bash); `--parents` keeps module paths. No native test tab in GHA (gap 3). |
| 3 | script `Stage build artifacts` (`main`/preprod/hardening) | `Stage build artifacts` (`if: != 'master'`): `mkdir -p "$RUNNER_TEMP/staging"` then identical `cp … \|\| true` lines | `$(Build.ArtifactStagingDirectory)` → `$RUNNER_TEMP/staging`, created with `mkdir -p`. |
| 3 | script `Stage build artifacts` (`master`) | `Stage build artifacts (master)`: `cp ./target/*.jar …` | |
| 4 | `PublishBuildArtifacts@1` `portfolio-api-canary` | `actions/upload-artifact@v4` `name: portfolio-api-canary-<variant>`, `path: ${{ runner.temp }}/staging`, `if-no-files-found: warn` | Per-variant suffix (`main`, `master`, `staging-preprod`, `staging-release-hardening`) because a matrix run uploads four artifacts into one run; `warn` mirrors ADO uploading an empty staging dir without failing. |
| 5 | script `Register artifact in Artifactory` (`main`) | `Register artifact in Artifactory` — same `publish_artifact.py` call, `--registry Artifactory` | `if: (push \|\| workflow_dispatch) && == 'main'`; env shims below; `mkdir -p` before the script writes its manifest. |
| 5 | script `Register artifact in artifact-registry` (other three) | `Register artifact in artifact-registry` — `--registry artifact-registry` | `if: (push \|\| workflow_dispatch) && != 'main'` |
| — | stage `displayName` | `Write canary run summary` (`$GITHUB_STEP_SUMMARY`) | Records which template branch each matrix leg exercised. |

## 5. Variable mapping

| ADO | GHA |
|---|---|
| `variables.artifactName` = `portfolio-api-canary` | `env.ARTIFACT_NAME` |
| `variables.templates_branch` = `${{ parameters.templateBranch }}` | job `env.TEMPLATE_BRANCH` = `${{ matrix.template_branch }}` |
| template param `jdkVersion: '17'` | `env.JDK_VERSION` |
| template param `mavenOptions` default | `env.MAVEN_OPTIONS` = `-B -DskipTests=false` |
| template param `mavenGoals` / `mavenGoal` default | literal per variant step (`clean package` / `package`) |
| `--registry` literal | literal per variant step (`Artifactory` / `artifact-registry`) |
| `$(Build.ArtifactStagingDirectory)` | `$RUNNER_TEMP/staging` (shimmed as `BUILD_ARTIFACTSTAGINGDIRECTORY` for the script) |
| `$(Build.SourcesDirectory)` | `$GITHUB_WORKSPACE` |
| `$(Build.BuildId)` | `${{ github.run_id }}` (also shimmed as `BUILD_BUILDID`) |
| `$(Build.SourceBranch)` | `${{ github.ref }}` (shimmed as `BUILD_SOURCEBRANCH`) |
| `$(Build.SourceVersion)` | `${{ github.sha }}` (shimmed as `BUILD_SOURCEVERSION`) |
| `$(Agent.Name)` | `${{ runner.name }}` (shimmed as `AGENT_NAME`) |
| ADO build URL | `PIPELINE_URL` = `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` (forward-compatible; `publish_artifact.py` builds no URL today) |

## 6. Condition mapping

| ADO | GHA |
|---|---|
| `${{ if eq(parameters.templateBranch, 'main') }}` (compile-time) | `if: matrix.template_branch == 'main'` (per step) |
| `${{ if eq(parameters.templateBranch, 'master') }}` | `if: matrix.template_branch == 'master'` |
| `${{ if eq(parameters.templateBranch, 'staging/preprod') }}` | `if: matrix.template_branch == 'staging/preprod'` |
| `${{ if eq(parameters.templateBranch, 'staging/release-hardening') }}` | `if: matrix.template_branch == 'staging/release-hardening'` |
| `${{ if eq(parameters.publishArtifacts, true) }}` (default `true`, never overridden) | always-on stage/upload steps; register steps additionally gated on event |
| — (ADO ran everything on every manual run) | register: `github.event_name == 'push' \|\| github.event_name == 'workflow_dispatch'` — never on `pull_request` |
| — | test-result steps `if: always()` |

## 7. Integration points

| Integration | ADO | GHA |
|---|---|---|
| Artifactory / artifact-registry | `publish_artifact.py` writes `<name>-manifest.json` into the staging dir | same script, unmodified; env shims supply the ADO variable names; skipped on PRs |
| Test results | `Maven@4.publishJUnitResults` | surefire XML uploaded as `test-results-<variant>` artifact |
| D2 notification | none in `build-java.yml` | n/a |
| Compliance attestation | none in `build-java.yml` | n/a |

No helper script changes were needed: `publish_artifact.py` does not construct ADO URLs and all
env vars it reads are shimmed.

## 8. Known gaps / behavioural differences

1. **No `pom.xml` in this repo** (pre-existing). Every branch's template runs Maven against
   `pom.xml` at the repo root; `services/portfolio-api/` contains only the two ADO YAMLs and the
   live ADO mirror run of pipeline 5 failed for that reason. The GHA workflow preserves this
   behaviour (fails at the Maven step) rather than inventing a project — fix by adding the source
   or pointing the template at the right directory.
2. **Registration on manual runs**. The playbook rule "register only on `push`" would make
   registration unreachable in a workflow with no push trigger. Because the ADO pipeline is
   manual-only and every manual ADO run registered, the guard is
   `push || workflow_dispatch` (still never on `pull_request`).
3. **Test results viewer**. GHA has no native test tab; results are artifacts. `dorny/test-reporter`
   can be added later if desired.
4. **Artifact naming**. ADO always published a single `portfolio-api-canary` artifact; GHA adds a
   `-<variant>` suffix so the `all` matrix can upload four. The registry name passed to
   `publish_artifact.py` is unchanged (`portfolio-api-canary`).
5. **Branch drift is frozen into the workflow**. ADO read the templates live from each branch;
   the GHA workflow inlines the variants as they exist today. If a template branch changes, this
   workflow must be updated (or, better, the branches unified and this workflow retired).
6. **Validation harness**: `validation/baselines/portfolio-api/` has no `test-counts.json`, so the
   "Test Baseline" scorecard check reports FAIL for every portfolio-api workflow. Creating a
   baseline needs real test counts from team-quant; none was invented here.

## 9. Secrets required

None. No step reads VG 201 `shared-ci-secrets`, and `publish_artifact.py` writes a local manifest only.
