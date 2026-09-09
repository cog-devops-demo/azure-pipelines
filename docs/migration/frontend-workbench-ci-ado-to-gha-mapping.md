# frontend-workbench-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `frontend-workbench-ci` (ID **106**), `services/frontend-workbench/azure-pipelines.yml` |
| Category | 2 — Alt-template consumer |
| Owner | team-frontend (last modified by s.wong@contoso.com) |
| Stack | Node.js 18.x / TypeScript (React client bundle + SSR bundle) |
| Templates consumed | `alt-templates/frontend/frontend-build.yml`, `alt-templates/frontend/frontend-deploy.yml` (×2) from `resources.repositories.ref: team/frontend-custom` |
| Variable groups | `shared-ci-secrets` (201), `frontend-cdn-config` (210) |
| ADO environments | `dev-frontend` (no checks), `staging-frontend` (approval: 1 × team-frontend) |
| Run history (snapshot 2026-03-17) | 62 runs / 58 succeeded / 3 failed / 1 cancelled, avg 12.3 min |
| GHA workflow | `.github/workflows/frontend-workbench-ci.yml` |
| Risk flags | R2 team-owned template branch never merged to `main`; R5 two `deployment:` jobs; R6 variable groups |

## Template resolution

The templates were read from the `team/frontend-custom` branch, **not** `main`, because that is
what the pipeline's `resources.repositories.ref` points at. Differences that matter:

| Template | `main` | `team/frontend-custom` (used) |
|---|---|---|
| `frontend-build.yml` | no Lighthouse step; artifact `<artifactName>` | adds `npx lhci autorun --collect.staticDistDir=build/ \|\| true`; artifact `<artifactName>-$(Build.BuildId)` |
| `frontend-deploy.yml` | identical | identical |

Note: the `team/frontend-custom` branch is not present in the `cog-devops-demo/azure-pipelines`
remote; it was read from the `COG-GTM/azure-pipelines` mirror of the same repository
(`git show team/frontend-custom:alt-templates/frontend/...`). The ADO MCP server
(`azure-devops-mcp`) fails to start in the migration environment, so `previewRun` could not be used
and templates were expanded manually.

Resolved parameters:

| Template | Parameter | Value |
|---|---|---|
| frontend-build.yml | `nodeVersion` | `18.x` |
| frontend-build.yml | `framework` | `react` |
| frontend-build.yml | `enableSSR` | `true` |
| frontend-build.yml | `artifactName` | `$(artifactName)` = `frontend-workbench-bundle` |
| frontend-deploy.yml (1) | `environment` | `dev` |
| frontend-deploy.yml (2) | `environment` | `staging` |
| frontend-deploy.yml (both) | `artifactName` | `frontend-workbench-bundle` |
| frontend-deploy.yml (both) | `cdnPurge` | default `true` |

### Expanded ADO execution order

1. Stage `Build` / job `build`: NodeTool@0 18.x → `npm ci` → `npm run lint` → `npm run build:react` → `npm run build:ssr` → `npm test -- --ci --coverage` → ArchiveFiles@2 (`build/` → `$(Build.ArtifactStagingDirectory)/frontend-workbench-bundle.zip`) → `npx lhci autorun ... || true` → PublishBuildArtifacts@1 (`frontend-workbench-bundle-$(Build.BuildId)`)
2. Stage `DeployFrontend_dev` / deployment `deploy_frontend`, environment `dev-frontend`: `download: current` → Upload to CDN (echo) → Purge CDN cache (echo) → Health check (`curl -sf https://dev.example.com/health`)
3. Stage `DeployFrontend_staging` / deployment `deploy_frontend`, environment `staging-frontend` (approval): same steps with `staging`

Stages 2 and 3 declare no `dependsOn` or `condition`, so ADO runs them sequentially after the previous stage succeeds, on every triggering push (see G1).

## Trigger mapping

| ADO | GHA | Note |
|---|---|---|
| `trigger.branches.include: [main, feature/*]` | `on.push.branches: [main, 'feature/**']` | `feature/*` (single level) intentionally broadened to `feature/**` (recursive) |
| `trigger.paths.include: [services/frontend-workbench/**]` | `on.push.paths: ['services/frontend-workbench/**', '.github/workflows/frontend-workbench-ci.yml']` | the workflow file itself is added to the filter (intentional; ADO had no equivalent — see G9) |
| — (no PR trigger) | `on.pull_request.branches: [main]` with the same paths | **added** for earlier CI feedback; deploy jobs are gated so PRs never deploy |
| `pool.vmImage: ubuntu-latest` | `runs-on: ubuntu-latest` | |

## Variable mapping

| ADO | GHA | Note |
|---|---|---|
| `variables.artifactName: frontend-workbench-bundle` | `env.ARTIFACT_NAME` | |
| `$(Build.ArtifactStagingDirectory)` | `env.BUILD_ARTIFACTSTAGINGDIRECTORY: ${{ github.workspace }}/staging` | created with `mkdir -p` in every job that uses it |
| `$(Build.BuildId)` (artifact suffix) | `${{ github.run_id }}` | |
| VG 210 `CDN_ENDPOINT`, `CDN_STORAGE_ACCOUNT` | `${{ vars.CDN_ENDPOINT }}`, `${{ vars.CDN_STORAGE_ACCOUNT }}` (environment variables) | |
| VG 210 `CDN_STORAGE_KEY`, `CDN_PURGE_API_KEY` (secret) | `${{ secrets.CDN_STORAGE_KEY }}`, `${{ secrets.CDN_PURGE_API_KEY }}` (environment secrets) | |
| VG 201 `shared-ci-secrets` | not mapped | no step in this pipeline reads it |

## Stage → job mapping

| ADO stage | ADO job | GHA job | `needs` | `if` | `environment` |
|---|---|---|---|---|---|
| `Build` ("Build frontend-workbench") | `build` | `build` | — | — | — |
| `DeployFrontend_dev` ("Deploy frontend to dev") | `deploy_frontend` (deployment) | `deploy_frontend_dev` | `build` | `github.event_name == 'push' && needs.build.outputs.service_changed == 'true'` | `dev-frontend` |
| `DeployFrontend_staging` ("Deploy frontend to staging") | `deploy_frontend` (deployment) | `deploy_frontend_staging` | `[build, deploy_frontend_dev]` | `github.event_name == 'push' && needs.build.outputs.service_changed == 'true'` | `staging-frontend` |

## Task / step mapping

### `build`

| # | ADO step | GHA step |
|---|---|---|
| 0 | implicit checkout | `actions/checkout@v4` |
| 1 | `NodeTool@0` `versionSpec: 18.x` | `actions/setup-node@v4` `node-version: '18.x'` |
| 2 | `script: npm ci` | `run: npm ci` (`working-directory: services/frontend-workbench`) |
| 3 | `script: npm run lint` | `run: npm run lint` |
| 4 | `script: npm run build:react` | `run: npm run build:react` |
| 5 | `${{ if eq(parameters.enableSSR, true) }}` → `npm run build:ssr` | `run: npm run build:ssr` (condition resolved at template-expansion time: always on) |
| 6 | `script: npm test -- --ci --coverage` | `run: npm test -- --ci --coverage` |
| 7 | `ArchiveFiles@2` root `build/`, `includeRootFolder: false`, zip → `$(Build.ArtifactStagingDirectory)/frontend-workbench-bundle.zip` | `mkdir -p "$BUILD_ARTIFACTSTAGINGDIRECTORY" && (cd build && zip -qr "$BUILD_ARTIFACTSTAGINGDIRECTORY/$ARTIFACT_NAME.zip" .)` |
| 8 | `script: npx lhci autorun --collect.staticDistDir=build/ \|\| true` | identical `run:` (still never fails the job) |
| 9 | `PublishBuildArtifacts@1` path `$(Build.ArtifactStagingDirectory)`, name `frontend-workbench-bundle-$(Build.BuildId)` | `actions/upload-artifact@v4` name `frontend-workbench-bundle-${{ github.run_id }}`, `if-no-files-found: error` |

### `deploy_frontend_dev` / `deploy_frontend_staging` (identical apart from `DEPLOY_ENVIRONMENT`)

| # | ADO step | GHA step |
|---|---|---|
| 0 | implicit checkout | `actions/checkout@v4` |
| 1 | — | `mkdir -p "$BUILD_ARTIFACTSTAGINGDIRECTORY"` (fresh runner) |
| 2 | `download: current` `artifact: frontend-workbench-bundle` | `actions/download-artifact@v4` name `frontend-workbench-bundle-${{ github.run_id }}` (see G2) |
| 3 | `script` "Upload to CDN" (echo) | same echoes + `test -f` on the zip so a missing bundle fails here rather than silently |
| 4 | `${{ if eq(parameters.cdnPurge, true) }}` → "Purge CDN cache" (echo) | `run:` echo (cdnPurge default true) |
| 5 | `script` "Health check" `curl -sf https://<env>.example.com/health \|\| exit 1` | identical, `<env>` from `$DEPLOY_ENVIRONMENT` |

## Condition mapping

| ADO | GHA |
|---|---|
| implicit `succeeded()` on stage order (`Build` → `DeployFrontend_dev` → `DeployFrontend_staging`) | `needs:` chain (`build` → `deploy_frontend_dev` → `deploy_frontend_staging`) |
| none on either deploy stage | `if: github.event_name == 'push'` — only needed because `pull_request` was added |
| trigger.paths (deploy stages implicitly only ran on service changes) | build.outputs.service_changed gate on both deploy jobs (workflow-only pushes build but do not deploy) |
| `${{ if eq(parameters.enableSSR, true) }}` | resolved to always-on at migration time |
| `${{ if eq(parameters.cdnPurge, true) }}` | resolved to always-on at migration time |
| `staging-frontend` approval check (1 × team-frontend, "Verify SSR bundle and CDN purge before promoting") | GitHub environment `staging-frontend` with a required-reviewers protection rule (must be configured in repo settings) |

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| Artifactory / `publish_artifact.py` | not used by this pipeline | not applicable |
| D2 / `notify_release_orchestrator.py` | not used | not applicable |
| Compliance attestation / `generate_attestation.py` | not used | not applicable |
| Test results | `npm test -- --ci --coverage`; no `PublishTestResults@2` in the template | same command; no results/coverage upload (equivalent to ADO — G4) |
| CDN upload / purge | `echo` placeholders in the team template | same placeholders; VG 210 values are exposed as env vars for when team-frontend implements them |

No `build-tools/scripts/` helper is called by this pipeline, so **no helper-script changes** were needed.

## Known gaps / behavioural differences

| ID | Description | Disposition |
|---|---|---|
| G1 | ADO YAML on `main` has **no branch guard on the staging deploy** (comment in the pipeline: "former main-branch-only guard on staging is lost, tracked as migration gap"). A `feature/*` push therefore promotes to staging once approved. Preserved as-is for functional equivalence; the `staging-frontend` approval is the only gate. | Pre-existing; team-frontend to decide whether to add `github.ref == 'refs/heads/main'` to `deploy_frontend_staging.if` |
| G2 | On `team/frontend-custom`, `frontend-build.yml` publishes `<artifactName>-$(Build.BuildId)` but `frontend-deploy.yml` downloads `<artifactName>` — an ADO name mismatch that would fail the download step. GHA uses the suffixed name in both places so the pipeline actually works. | Intentional fix; documented |
| G3 | `feature/*` → `feature/**` (recursive) broadens the branch filter to nested `feature/x/y` branches. | Intentional |
| G4 | No test-result or coverage artifact is uploaded (ADO template has none either). | Pre-existing; optional follow-up: `actions/upload-artifact` for `coverage/` |
| G5 | Health check URL is hard-coded to `https://<env>.example.com/health` in the team template; kept verbatim. | Pre-existing |
| G6 | ~~services/frontend-workbench/ contained only the ADO YAML~~ — resolved: the runnable Node scaffold (package.json, scripts/, tests/) now exists on main; the build job runs for real. | Resolved |
| G7 | ADO's `feature/*` push previously also deployed to dev without approval; identical in GHA (`dev-frontend` has no protection rules). | Pre-existing |
| G8 | `validation/baselines/frontend-workbench/` does not exist, so the migration validator reports **Artifact Baseline: FAIL** and **Test Baseline: FAIL** ("No … baseline found"). The baseline must come from a real ADO run of pipeline 106 (artifact listing + test-result summary); it has not been invented here. | Requires team-frontend / platform to capture a baseline from ADO |
| G9 | Trigger paths additionally include the workflow file so workflow-only changes exercise the build (deferred until the service source landed on main; now enabled). Workflow-only pushes build only and never deploy. | Intentional |

## Required GitHub configuration

Environments (Settings → Environments):

| Environment | Protection | Variables | Secrets |
|---|---|---|---|
| `dev-frontend` | none (as in ADO) | `CDN_ENDPOINT`, `CDN_STORAGE_ACCOUNT` | `CDN_STORAGE_KEY`, `CDN_PURGE_API_KEY` |
| `staging-frontend` | required reviewers: team-frontend (≥ 1) | `CDN_ENDPOINT`, `CDN_STORAGE_ACCOUNT` | `CDN_STORAGE_KEY`, `CDN_PURGE_API_KEY` |

Secrets required: `CDN_STORAGE_KEY`, `CDN_PURGE_API_KEY` (per environment). No repository-level secrets are needed; nothing from `shared-ci-secrets` is consumed.
