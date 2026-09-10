# frontend-workbench-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `frontend-workbench-ci` (ADO ID **106**, inventory row `frontend-workbench-ci (106)`) |
| ADO YAML | `services/frontend-workbench/azure-pipelines.yml` |
| Category | 2 — alt-template consumer |
| Stack | Node 18 / React (client bundle + SSR bundle) |
| Owner | team-frontend |
| Pool | `Azure Pipelines` hosted, `ubuntu-latest` |
| Template source | `shared-ci-platform` @ **`team/frontend-custom`** |
| GHA workflow | `.github/workflows/frontend-workbench-ci.yml` |
| Helper scripts (`build-tools/scripts/`) | none referenced by this pipeline or its templates — **no script changes** |

## 1. Template resolution

`resources.repositories.templates` points at `shared-ci-platform` ref `team/frontend-custom`. That branch does not exist in this repository (only `main`), so the templates were resolved from the live Azure DevOps repo `danagajewski/danagajewski-demo/shared-ci-platform` via the Git REST API and compared against this repo's `main`:

| Template | `team/frontend-custom` (`ce3ed1b1`) vs local `main` | `team/frontend-custom` vs ADO `main` (`47f9464e`) |
|---|---|---|
| `alt-templates/frontend/frontend-build.yml` | **identical** | team branch keeps the `projectDirectory` parameter and applies `workingDirectory` to every script step and to the archive root; ADO `main` does not |
| `alt-templates/frontend/frontend-deploy.yml` | **identical** | identical |

The expanded view below therefore uses the local copies, which are byte-for-byte the templates ADO actually runs.

**ADO MCP verification:** the `azure-devops-mcp` server available in this session is bound to org `shawn0864` (projects `ado_org`, `shawn`); `pipelines_definition` for project `danagajewski-demo` returned `TF200016: project does not exist`. Verification was done instead with direct REST calls to `dev.azure.com/danagajewski/danagajewski-demo` using the provisioned service-principal credentials: definition `frontend-workbench-ci` (local definition id 8), recent runs 42/78/96 all produce artifact `frontend-workbench-bundle`, fail in the dev stage on the `Health check` step (`https://dev.example.com/health` is unreachable) and skip the staging stage. Run 96 was a pull-request validation build and still executed the dev deploy stage.

## 2. Expanded ADO execution view (source of truth)

```
Stage Build ("Build frontend-workbench") — job build, ubuntu-latest
  NodeTool@0                versionSpec 18.x
  script  npm ci                                 wd: services/frontend-workbench
  script  npm run lint                           wd: services/frontend-workbench
  script  npm run build:react                    wd: services/frontend-workbench   (framework=react)
  script  npm run build:ssr                      wd: services/frontend-workbench   (enableSSR=true)
  script  npm test -- --ci --coverage            wd: services/frontend-workbench
  ArchiveFiles@2            root services/frontend-workbench/build/, includeRootFolder false, zip
                            → $(Build.ArtifactStagingDirectory)/frontend-workbench-bundle.zip
  PublishBuildArtifacts@1   pathToPublish $(Build.ArtifactStagingDirectory), artifactName frontend-workbench-bundle

Stage DeployFrontend_dev ("Deploy frontend to dev") — deployment job deploy_frontend, runOnce,
                                                      environment dev-frontend, no dependsOn/condition
  checkout: self
  DownloadBuildArtifacts@1  buildType current, downloadType single, artifactName frontend-workbench-bundle,
                            downloadPath $(Pipeline.Workspace)
  script  "Upload to CDN"        echo only
  script  "Purge CDN cache"      echo only (cdnPurge default true)
  script  "Health check"         curl -sf https://dev.example.com/health || exit 1

Stage DeployFrontend_staging ("Deploy frontend to staging") — same template, environment staging-frontend,
                                                              no dependsOn/condition
  (same five steps with environment=staging)
```

## 3. Trigger mapping

| ADO | GHA | Note |
|---|---|---|
| `trigger.branches.include: [main, feature/*]` | `on.push.branches: [main, 'feature/**']` | **Intentional change:** ADO `feature/*` matches one path segment; GHA `feature/**` also matches `feature/a/b`. |
| `trigger.paths.include: [services/frontend-workbench/**]` | `on.push.paths: [services/frontend-workbench/**, .github/workflows/frontend-workbench-ci.yml]` | Workflow file added so workflow-only edits are exercised. |
| implicit PR validation trigger (ADO default `pr:` — all target branches, no path filter) | `on.pull_request.branches: [main]` with the same `paths` filter | Explicit per playbook. Narrower than ADO's implicit trigger (ADO ran on every PR regardless of paths — see run 96). |
| no `schedules` | none | |

## 4. Stage → job mapping

| ADO stage | GHA job | `needs` | `environment` | Steps |
|---|---|---|---|---|
| `Build` | `build` | — | — | 9 |
| `DeployFrontend_dev` | `deploy_frontend_dev` | `build` | `dev-frontend` | 5 |
| `DeployFrontend_staging` | `deploy_frontend_staging` | `deploy_frontend_dev` | `staging-frontend` | 5 |

ADO stages without `dependsOn` run sequentially in file order, which is what the `needs` chain reproduces (staging is skipped when dev fails, as in ADO).

## 5. Task → step mapping

| ADO task / step | GHA step | Translation |
|---|---|---|
| implicit checkout / `checkout: self` | `actions/checkout@v4` | first step of every job |
| `NodeTool@0` `versionSpec: 18.x` | `actions/setup-node@v4` `node-version: '18.x'` | |
| `script: npm ci` | `run: npm ci` | job-level `defaults.run.working-directory: services/frontend-workbench` replaces `workingDirectory` |
| `script: npm run lint` | `run: npm run lint` | |
| `script: npm run build:react` | `run: npm run build:react` | `${{ parameters.framework }}` resolved to `react` |
| `${{ if eq(parameters.enableSSR, true) }}` → `npm run build:ssr` | `run: npm run build:ssr` | compile-time condition is true for this pipeline, so the step is unconditional |
| `script: npm test -- --ci --coverage` | `run: npm test -- --ci --coverage` | verbatim; `scripts/test.js` ignores the extra flags in both systems |
| `ArchiveFiles@2` (zip, `includeRootFolder: false`) | `mkdir -p "$BUILD_ARTIFACTSTAGINGDIRECTORY" && (cd build && zip -qr ".../frontend-workbench-bundle.zip" .)` | archive contains the *contents* of `build/` (`client/bundle.js`, `index.html`, `ssr/server.js`) at the zip root, same as ADO |
| `PublishBuildArtifacts@1` | `actions/upload-artifact@v4` `name: frontend-workbench-bundle`, `path: $BUILD_ARTIFACTSTAGINGDIRECTORY`, `if-no-files-found: error` | |
| `DownloadBuildArtifacts@1` (`downloadType: single`) | `actions/download-artifact@v4` `name: frontend-workbench-bundle`, `path: $PIPELINE_WORKSPACE/frontend-workbench-bundle` | same on-disk layout as ADO (`$(Pipeline.Workspace)/<artifactName>/`) |
| `script "Upload to CDN"` | `run:` echo | verbatim, `${{ parameters.environment }}` → `$DEPLOY_ENVIRONMENT` |
| `${{ if eq(parameters.cdnPurge, true) }}` → `script "Purge CDN cache"` | `run:` echo | `cdnPurge` defaults to `true` and is not overridden, so unconditional |
| `script "Health check"` | `run: curl -sf "https://$DEPLOY_ENVIRONMENT.example.com/health" \|\| exit 1` | verbatim, including the placeholder host |
| `deployment` job + `environment: dev-frontend` / `staging-frontend` | job `environment:` | protection rules must be recreated in GitHub (see §9) |

## 6. Variable mapping

| ADO | GHA | Note |
|---|---|---|
| `variables.artifactName` = `frontend-workbench-bundle` | top-level `env.ARTIFACT_NAME` | |
| template param `projectDirectory` | `env.PROJECT_DIRECTORY` + job `defaults.run.working-directory` | |
| `$(Build.ArtifactStagingDirectory)` | `env.BUILD_ARTIFACTSTAGINGDIRECTORY` = `${{ github.workspace }}/artifact-staging` | created with `mkdir -p` before use |
| `$(Pipeline.Workspace)` | `env.PIPELINE_WORKSPACE` = `${{ github.workspace }}/pipeline-workspace` | download-artifact creates it |
| `${{ parameters.environment }}` | job `env.DEPLOY_ENVIRONMENT` (`dev` / `staging`) | |
| VG `frontend-cdn-config` → `CDN_ENDPOINT`, `CDN_STORAGE_ACCOUNT` | `${{ vars.CDN_ENDPOINT }}`, `${{ vars.CDN_STORAGE_ACCOUNT }}` (environment variables) | plain values in ADO |
| VG `frontend-cdn-config` → `CDN_STORAGE_KEY`, `CDN_PURGE_API_KEY` | `${{ secrets.CDN_STORAGE_KEY }}`, `${{ secrets.CDN_PURGE_API_KEY }}` (environment secrets) | secret in ADO |
| VG `shared-ci-secrets` (attached to definition 106) | not mapped | no step of this pipeline reads it |
| Service connections `AzureSubscription-Dev` / `AzureSubscription-Staging` | not mapped | listed on the definition, but the deploy template contains no `AzureCLI`/`AzureFileCopy` task that uses them; when the echo steps are replaced with real uploads, use OIDC federated credentials rather than copying SP keys |
| `PIPELINE_URL` / other ADO env shims (`BUILD_SOURCEBRANCH`, …) | not needed | no helper script is invoked |

The variable group is referenced only at the ADO definition level (not in the YAML), and the inlined deploy template only echoes. The four values are exposed to both deploy jobs so a future real CDN upload/purge has them, but nothing consumes them today.

## 7. Condition mapping

| ADO | GHA | Note |
|---|---|---|
| `${{ if eq(parameters.enableSSR, true) }}` | none (step always present) | resolved at template-expansion time |
| `${{ if eq(parameters.cdnPurge, true) }}` | none (step always present) | resolved at template-expansion time |
| stage `condition` on `DeployFrontend_dev` | none | ADO has none |
| stage `condition` on `DeployFrontend_staging` | **none — deliberately** | see Known gaps #1 |
| stage `dependsOn` | `needs` | implicit sequential order |

## 8. Integration points

| Integration | ADO | GHA |
|---|---|---|
| Test results | none — `npm test` prints the `node:test` TAP summary to the log; no `PublishTestResults@2` | same: log only. No test artifact is uploaded because none exists in ADO (see Known gaps #3). |
| Artifactory (`publish_artifact.py`) | not used | not applicable |
| D2 release-orchestrator notification | not used | not applicable |
| Compliance attestation | not used | not applicable |
| CDN upload / purge | echo placeholders | echo placeholders, VG values exposed as env |

## 9. Secrets, variables and environments required in GitHub

| Kind | Name | Scope | Source |
|---|---|---|---|
| Environment | `dev-frontend` | no protection rules (matches ADO) | ADO environment id 5 |
| Environment | `staging-frontend` | required reviewers: team-frontend (1), instructions "Verify SSR bundle and CDN purge before promoting" | ADO environment id 6 |
| Environment variable | `CDN_ENDPOINT` | both environments | VG `frontend-cdn-config` |
| Environment variable | `CDN_STORAGE_ACCOUNT` | both environments | VG `frontend-cdn-config` |
| Environment secret | `CDN_STORAGE_KEY` | both environments | VG `frontend-cdn-config` (secret) |
| Environment secret | `CDN_PURGE_API_KEY` | both environments | VG `frontend-cdn-config` (secret) |

No values are hardcoded in the workflow. The workflow runs with `permissions: contents: read`.

## 10. Known gaps and behavioural differences

1. **Staging deploy has no main-branch guard (pre-existing, preserved).** The ADO YAML comment records that `frontend-deploy.yml` has no `condition` parameter, so the former main-only guard on `DeployFrontend_staging` was lost. The GHA job has no `if:` either, so `feature/**` pushes (and PRs) reach the `staging-frontend` gate exactly as in ADO. Recommended follow-up (outside this migration): `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` on `deploy_frontend_staging`, and the same fix in the ADO template.
2. **Deploy stages run on pull requests (pre-existing, preserved).** Neither ADO deploy stage is conditioned on the event, and ADO run 96 (PR build) executed the dev deploy. The GHA workflow mirrors this; the deploy steps are echo-only so nothing external is mutated.
3. **Health check fails (pre-existing, preserved).** `https://dev.example.com/health` is a placeholder; every inspected ADO run fails at this step and skips staging. The GHA run of this commit is expected to fail in `deploy_frontend_dev` for the same reason — this is parity, not a migration defect. It also means the `staging-frontend` gate is never reached in either system until the host is fixed.
4. **No test report in either system.** `npm test -- --ci --coverage` runs `node --test` with TAP output; ADO publishes nothing to its Tests tab and no `.trx`/JUnit exists to upload in GHA. The validator's runtime-parity test comparison can therefore only report "not measured" on both sides. If a report is wanted, add `--test-reporter=junit` to `scripts/test.js` and a `PublishTestResults@2` / `actions/upload-artifact@v4` pair in *both* pipelines.
5. **`feature/*` → `feature/**`** (intentional broadening, §3).
6. **PR trigger is path-filtered**, whereas ADO's implicit PR trigger ran on every PR in the repo (§3).
7. **`team/frontend-custom` is not mirrored in this repo.** Templates were fetched from ADO and match local `main`; if the team branch diverges later, this workflow will not pick it up because the logic is inlined.
8. **Approval instructions** on `staging-frontend` are free text in ADO; GitHub environments have no equivalent field.
9. **Retention:** ADO 30 days / min 5 builds; GHA artifacts use the repository default (90 days max).

## 11. Local verification performed

- `npm ci && npm run lint && npm run build:react && npm run build:ssr && npm test -- --ci --coverage` in `services/frontend-workbench` (Node 20 locally): 4/4 tests pass, `build/` contains `client/bundle.js`, `index.html`, `ssr/server.js`.
- `actionlint .github/workflows/frontend-workbench-ci.yml`: clean.
- `validation/scripts/validate_migration.py --service frontend-workbench …`: 5/5 blocking checks PASS, both advisory baselines PASS.
