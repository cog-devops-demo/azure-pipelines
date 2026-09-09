# market-sim-ci — ADO → GitHub Actions mapping

| | |
|---|---|
| ADO pipeline | `market-sim-ci` (ID **108**) |
| ADO YAML | `services/market-sim/azure-pipelines.yml` |
| GHA workflow | `.github/workflows/market-sim-ci.yml` |
| Category | 4 — Custom inline (no shared templates) |
| Template branch | none |
| Stack | Rust (rustup stable / cargo) |
| Pool | `ubuntu-latest` (Microsoft-hosted) |
| Owner | team-quant (low confidence per inventory) |
| Risk flags | R11 no template reuse; R12 ADO-specific constructs; R13 deploys outside release-orchestrator |

## Template resolution

None required. The pipeline is fully inline; no `resources.repositories` block, no
`template:` references. `templates/build/build-rust.yml` exists in the repo but is not
consumed by pipeline 108 and was intentionally **not** inlined.

ADO MCP verification (`azure-devops-mcp` → `pipeline_get_pipeline` 108 /
`pipeline_preview_pipeline_yaml`) could not run — the MCP server process failed to start in
the session. Fallback: manual expansion, which is trivial here because there is nothing to
expand. Pipeline metadata was taken from `docs/pipeline-inventory-report.md` and
`docs/samples/ado-api-responses.json` (id 108, `queueStatus: enabled`, revision 11).

## Trigger mapping

| ADO | GHA | Notes |
|---|---|---|
| `trigger.branches.include: [main]` | `on.push.branches: [main]` | |
| `trigger.paths.include: [services/market-sim/**]` | `on.push.paths: ['services/market-sim/**']` | GHA path filters support `**` natively |
| *(none)* | `on.pull_request` (branches `main`, same path filter) | **Intentional addition** — earlier CI feedback on PRs |
| *(none)* | `on.workflow_dispatch` | **Intentional addition** — manual re-run |

## Stage → job mapping

| ADO stage / job | GHA job | `needs` | Condition |
|---|---|---|---|
| `Build` / `build_rust` ("Rust build", `timeoutInMinutes: 30`) | `build` (`timeout-minutes: 30`) | — | always |
| `Deploy` / `deploy` (`dependsOn: Build`) | `deploy` | `build` | `github.event_name == 'push' && github.ref == 'refs/heads/main'` |

### Step-by-step correspondence — `Build`

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 0 | implicit checkout | `actions/checkout@v4` | |
| 1 | `script` "Install Rust" — rustup + `##vso[task.prependpath]$HOME/.cargo/bin` | `run` "Install Rust" | `##vso[task.prependpath]` → `echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"`. Runs in `${{ github.workspace }}` (ADO step had no `workingDirectory`) |
| 2 | `script: cargo fetch` (`workingDirectory: services/market-sim`) | `run: cargo fetch` | `workingDirectory` → job-level `defaults.run.working-directory` |
| 3 | `script: cargo clippy -- -D warnings` | `run: cargo clippy -- -D warnings` | identical |
| 4 | `script: cargo build --release` | `run: cargo build --release` | identical |
| 5 | `script: cargo test -- --test-threads=1` | `run: cargo test -- --test-threads=1` | identical |
| 6 | `script: cp target/release/market-sim $(Build.ArtifactStagingDirectory)/` | `run: mkdir -p "$RUNNER_TEMP/staging" && cp …` | `$(Build.ArtifactStagingDirectory)` → `$RUNNER_TEMP/staging`; `mkdir -p` added because GHA does not pre-create the directory |
| 7 | `PublishBuildArtifacts@1` (`pathToPublish: $(Build.ArtifactStagingDirectory)`, `artifactName: market-sim-binary`) | `actions/upload-artifact@v4` (`name: market-sim-binary`, `path: ${{ runner.temp }}/staging`, `if-no-files-found: error`) | |

### Step-by-step correspondence — `Deploy`

| # | ADO step | GHA step | Translation |
|---|---|---|---|
| 0 | implicit checkout | `actions/checkout@v4` | |
| 1 | `script` "Deploy to cluster" (two `echo` lines) | `run` "Deploy to cluster" | Preserved verbatim (R13). Real deploy mechanism is undocumented in ADO too |

## Task mapping

| ADO task | GHA equivalent |
|---|---|
| `script` | `run` |
| `##vso[task.prependpath]<dir>` | `echo "<dir>" >> "$GITHUB_PATH"` |
| `PublishBuildArtifacts@1` | `actions/upload-artifact@v4` |
| `workingDirectory:` (per step) | `defaults.run.working-directory` (job) + per-step override |
| `timeoutInMinutes` | `timeout-minutes` |
| `pool.vmImage` | `runs-on` |

## Variable mapping

| ADO | GHA |
|---|---|
| `variables.CARGO_TERM_COLOR: 'always'` | `env.CARGO_TERM_COLOR: always` |
| `variables.RUST_BACKTRACE: 1` | `env.RUST_BACKTRACE: 1` |
| `$(Build.ArtifactStagingDirectory)` | `$RUNNER_TEMP/staging` / `${{ runner.temp }}/staging` |
| `variables['Build.SourceBranch']` | `github.ref` |

No variable groups; no helper scripts from `build-tools/` are called, so no env shims
(`BUILD_SOURCEBRANCH`, `PIPELINE_URL`, …) are needed.

## Condition mapping

| ADO | GHA |
|---|---|
| `dependsOn: Build` | `needs: build` |
| `and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))` | `needs: build` (implies success) + `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` |

The `github.event_name == 'push'` clause is stricter than ADO: with the added
`pull_request` trigger a PR targeting `main` would otherwise never match `refs/heads/main`
anyway (PR refs are `refs/pull/N/merge`), but the explicit guard documents the intent and
protects against `workflow_dispatch` runs on `main`.

## Integration points

| Integration | ADO | GHA |
|---|---|---|
| Artifactory / `publish_artifact.py` | not used | not applicable |
| D2 / release-orchestrator notification | not used — deploy is explicitly "managed outside D2" | not applicable; echo preserved verbatim |
| Compliance attestation | not used | not applicable |
| Test results | `cargo test` exit status only (no `PublishTestResults@2`) | `cargo test` exit status only |
| Build artifact | `market-sim-binary` (ADO artifact) | `market-sim-binary` (GHA artifact, default 90-day retention) |

## Known gaps / behavioural differences

- **Added triggers**: `pull_request` and `workflow_dispatch` did not exist in ADO.
- **Deploy is echo-only** in both systems. The actual compute-cluster deploy mechanism
  (R13) is undocumented; team-quant must confirm before ADO 108 is disabled.
- **`ContainerRegistry-ACR` service connection** is bound to pipeline 108 in the ADO API
  snapshot but nothing in the YAML uses it; nothing was added in GHA.
- **Artifact retention**: ADO retention policy vs GHA default 90 days — adjust
  `retention-days` if the ADO policy differs.
- **No Rust source on `main`**: `services/market-sim/` currently contains only the ADO
  YAML, so the workflow will fail at `cargo fetch` until the crate is committed. Path
  filtering means the workflow does not trigger on this PR.
- `validation/baselines/market-sim/*` values were carried over from the measured run in the
  earlier migration attempt (PR #3: 1 release binary ≈473 KB, 4 `cargo test` tests against
  the scaffold in COG-GTM/azure-pipelines#12); re-measure once the crate lands here.

## Secrets required

None. The workflow references no `${{ secrets.* }}`.
