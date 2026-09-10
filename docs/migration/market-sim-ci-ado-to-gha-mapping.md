# market-sim-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `market-sim-ci` (inventory ID 108; live definition id 2 in `danagajewski/danagajewski-demo`) |
| ADO YAML | `services/market-sim/azure-pipelines.yml` |
| GHA workflow | `.github/workflows/market-sim-ci.yml` |
| Stack | Rust (stable via rustup) |
| Category | 4 — custom inline YAML, no shared templates |
| Owner | team-quant? (low confidence per inventory) |
| Pool | `ubuntu-latest` (hosted) → `runs-on: ubuntu-latest` |

## Source analysis

The pipeline declares no `resources.repositories` and no `template:` references, so there was
nothing to resolve from a template branch; every step below is inline in the service YAML.
`templates/build/build-rust.yml` exists in the repo but is **not** consumed by pipeline 108 and
was not inlined.

ADO MCP verification: the `azure-devops-mcp` server in this session is bound to org `shawn0864`
(projects `ado_org`, `shawn`) and cannot see `danagajewski/danagajewski-demo`. Verification was
done instead against the ADO REST API with the same service-principal credentials the
`validate-migration` workflow uses. Findings from the most recent run (build 92, PR #33 merge
commit, `succeeded`):

- Timeline: Install Rust → Fetch dependencies → Lint with clippy → Build release binary →
  Run tests → Stage binary → Publish market-sim binary; stage `Deploy market-sim` **skipped**
  (PR build, not `refs/heads/main`). Matches the YAML on `main`.
- Artifacts: exactly one, `market-sim-binary`.
- Test runs published to ADO: **none** (cargo output is only in the build log; 4 tests pass).
- Definition is `enabled` and runs on GitHub pull requests as well as pushes.

## Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger.branches.include: [main]` | `on.push.branches: [main]` | |
| `trigger.paths.include: [services/market-sim/**]` | `on.push.paths: ['services/market-sim/**', '.github/workflows/market-sim-ci.yml']` | Workflow file added to its own path filter so edits to the workflow are exercised. |
| (none) | `on.pull_request` (`main`, same paths) | **Intentional addition** — earlier CI feedback; the live ADO definition already builds PRs via its GitHub PR validation setting, so this matches observed behaviour. |
| (none) | `workflow_dispatch` | Manual re-run convenience. |

## Variables

| ADO `variables:` | GHA top-level `env:` |
|---|---|
| `CARGO_TERM_COLOR: 'always'` | `CARGO_TERM_COLOR: always` |
| `RUST_BACKTRACE: 1` | `RUST_BACKTRACE: 1` |

No variable groups are bound to this pipeline (inventory §7.2). No secrets are required.

## Stage → job mapping

| ADO stage / job | GHA job | `needs` | Condition |
|---|---|---|---|
| `Build` / `build_rust` ("Rust build", `timeoutInMinutes: 30`) | `build` ("Build market-sim", `timeout-minutes: 30`) | — | — |
| `Deploy` / `deploy` (`dependsOn: Build`) | `deploy` ("Deploy market-sim") | `build` | see below |

### Condition mapping

| ADO | GHA |
|---|---|
| `and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))` | `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` — `succeeded()` is implied by `needs: build`; `event_name == 'push'` additionally keeps the added `pull_request` and `workflow_dispatch` triggers out of the deploy job (on ADO the stage was skipped on PR builds anyway because the branch is `refs/pull/N/merge`). |

## Step / task mapping (Build job)

`workingDirectory: services/market-sim` on each ADO cargo step → `defaults.run.working-directory:
services/market-sim` on the job; the rustup step overrides it back to `${{ github.workspace }}`.

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 0 | implicit `checkout` | `actions/checkout@v4` | |
| 1 | `script` "Install Rust": rustup install + `##vso[task.prependpath]$HOME/.cargo/bin` | `run:` same curl/rustup line + `echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"` | Logging command → `$GITHUB_PATH` file. |
| 2 | `script: cargo fetch` | `run: cargo fetch` | verbatim |
| 3 | `script: cargo clippy -- -D warnings` | `run: cargo clippy -- -D warnings` | verbatim |
| 4 | `script: cargo build --release` | `run: cargo build --release` | verbatim |
| 5 | `script: cargo test -- --test-threads=1` | `run: cargo test -- --test-threads=1` | verbatim |
| 6 | `script`: `cp target/release/market-sim $(Build.ArtifactStagingDirectory)/` | `mkdir -p "$RUNNER_TEMP/staging"; cp target/release/market-sim "$RUNNER_TEMP/staging/"` | `$(Build.ArtifactStagingDirectory)` → `$RUNNER_TEMP/staging`; ADO pre-creates the staging dir, GHA does not, hence `mkdir -p`. |
| 7 | `PublishBuildArtifacts@1` (`pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: market-sim-binary`) | `actions/upload-artifact@v4` (`name: market-sim-binary`, `path: ${{ runner.temp }}/staging`, `if-no-files-found: error`) | Same artifact name so runtime parity can match it. |

## Step mapping (Deploy job)

| ADO step | GHA step |
|---|---|
| implicit `checkout` | `actions/checkout@v4` |
| `script` "Deploy to cluster" (two `echo` lines) | `run:` identical two `echo` lines — preserved verbatim, per the inventory note that this deployment is "managed outside D2". No real deploy logic was added. |

## Integration points

| Integration | ADO behaviour | GHA behaviour |
|---|---|---|
| Artifactory (`publish_artifact.py`) | not used | not used |
| D2 release orchestrator (`notify_release_orchestrator.py`) | not used — deploy step explicitly says "managed outside D2" | not used; there is still no deployment record for this service anywhere |
| Compliance attestation | not used | not used |
| Test results (`PublishTestResults@2`) | not used — cargo output only in log | not used; no test-report artifact is published (see gaps) |
| `ContainerRegistry-ACR` service connection | bound to the ADO definition, **never referenced by the YAML** (no `Docker@2`, no image push) | **not recreated.** No `ACR_*` secrets and no push step were added; the binding appears unused and should be verified with team-quant before any registry credential is created on GitHub. |

## Helper scripts

The pipeline calls nothing under `build-tools/scripts/`, so no helper-script changes were needed
and none were made.

## Secrets required

None. The workflow uses only `contents: read` on the default `GITHUB_TOKEN`.

## Known gaps / behavioural differences

1. **Test parity is unmeasurable on both sides.** ADO publishes no test run (0 tests in the
   ADO Test API) and the GHA workflow publishes no JUnit/TRX artifact, so `parity_report.py`
   reports `Tests run: 0 / not measured → EXCEPTION`, not PASS. This is faithful to ADO: adding a
   JUnit artifact on the GHA side (e.g. via `cargo2junit`) would make ADO's `0` and GHA's `4`
   disagree and turn the exception into a MISMATCH. If test-count parity is wanted, add
   `PublishTestResults@2` to the ADO pipeline first, then mirror it here.
2. **Deploy job is echo-only**, exactly as in ADO. Whatever really deploys market-sim lives
   outside this repo and outside D2; the migration neither found nor changed it.
3. **`ContainerRegistry-ACR` binding not migrated** (see integration table) — documented, not
   reproduced.
4. **Extra triggers** (`pull_request`, `workflow_dispatch`) are additive; the deploy guard makes
   them no-ops for deployment.
5. **Rust toolchain** — the rustup installer is run verbatim as in ADO even though
   `ubuntu-latest` GitHub runners ship rustup; a future cleanup could switch to
   `dtolnay/rust-toolchain@stable` plus `Swatinem/rust-cache`, but that was out of scope for a
   like-for-like migration.
6. **Artifact retention** — ADO retention (30 days / min 5 builds) vs GHA default 90 days; no
   `retention-days` set, so the repo default applies.
