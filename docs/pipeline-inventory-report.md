# ADO Pipeline Inventory & Migration Disposition Report

**Project:** `contoso-financial/shared-ci-platform` (mirrored here as `cog-devops-demo/azure-pipelines`)
**Sources:** `docs/samples/ado-api-responses.json` (ADO REST dump, generated 2026-03-17) cross-checked against every pipeline/template YAML in this repository.
**Scope:** every pipeline definition registered in ADO (18) plus every pipeline-shaped YAML entrypoint in the repo that ADO does *not* know about.

## 1. Executive summary

| Disposition | Count | Pipelines |
|---|---|---|
| **Migrate** to GitHub Actions | 7 | pricing-engine-ci, portfolio-api-ci, portfolio-api-canary, risk-batch-ci, frontend-workbench-ci, market-sim-ci, ops-control-plane-ci |
| **Do not migrate** — non-build workload, move to job/compute platform | 7 | regulatory-reporting-ci, notebook-executor-nightly, scenario-runner-weekly, var-scenario-sweep-nightly, daily-positions-export, attestation-backfill-weekly, bulk-reprocess-trades |
| **Dead** — retire/delete | 5 | risk-batch-legacy, onetime-data-migration, old-pricing-pipeline, batch-runner-v1, `archive/old-release-workflow.yml` (unregistered) |

Headline risks:

1. **Template branches are missing from this repo.** Pipeline YAML references seven template branches (`master`, `staging/preprod`, `staging/release-hardening`, `team/frontend-custom`, `team/quant-experiments`, `team/reporting-hotfix`, `legacy/master-support`). Only `main` exists on `origin`. Every template resolution below was done against `main`; the actual drift on those branches (e.g. the retry logic `risk-batch-ci` depends on, the SSR steps `frontend-workbench-ci` depends on) **cannot be verified from this repository** and must be pulled from the ADO `shared-ci-platform` TfsGit repo before migration is declared equivalent.
2. **6 of 18 registered pipelines have no owner** (`owner_team` = unknown/none), including one production build pipeline (`pricing-engine-ci`) and two scheduled compute jobs that write to internal systems.
3. **Six pipeline YAMLs reference source that is not in the repo** (107, 110, 111, 115, 116, 118 — `services/regulatory-reporting/src`, `services/scenario-runner/src`, `services/notebook-executor/notebooks`, `adhoc/scripts/*.py`, `batch_runner/`; full list in §7.4). Their behaviour can only be inferred from the YAML + ADO run history.
4. **The three template-based release pipelines (101, 102, 104) have hidden downstream coupling** via `build-tools/scripts/*` — Artifactory registration, D2 release notifications, attestation-database writes — that is not visible in the service YAML because it is buried in the shared templates. The inline pipelines (108, 109) have the opposite problem: ADO binds them to ACR/K8s credentials their YAML never uses.
5. **Non-build workloads use ~16× more agent-time than builds.** Over the 90-day window (`build_runs_summary`, runs × avg duration) the 7 non-build pipelines consumed ≈ 41,500 agent-minutes vs ≈ 2,600 for the 7 build pipelines; all but one (`bulk-reprocess-trades`) run on self-hosted pools with internal network access and cannot land on GitHub-hosted runners.

## 2. Full inventory

Legend — **Trigger:** CI = branch/path CI trigger, SCHED = cron, MANUAL = `trigger: none`, no schedule. **90d runs** from `build_runs_summary`. Owner from ADO `_meta.owner_team`; ⚠ = unknown/none/contested.

| ID | Pipeline | YAML | Stack | Pool | Trigger | Template source (branch) | Owner | Last run / result | 90d runs (avg min) | Disposition |
|---|---|---|---|---|---|---|---|---|---|---|
| 101 | pricing-engine-ci | `services/pricing-engine/azure-pipelines.yml` | .NET 8 | Azure Pipelines (hosted) | CI `main`, `release/*` | central `build-dotnet`, `run-tests`, `release-standard` (`main`) | ⚠ unknown (ex-contractor; shared-ci-platform best-effort) | 2026-03-14 succeeded | 47 (7.5) | **Migrate** |
| 102 | portfolio-api-ci | `services/portfolio-api/azure-pipelines.yml` | Java 17 / Maven | hosted | CI `main`, `master` | central `build-java`, `release-standard` (**`master`**) | team-quant | 2026-03-12 succeeded | 31 (9.8) | **Migrate** |
| 103 | portfolio-api-canary | `services/portfolio-api/azure-pipelines-canary.yml` | Java 17 / Maven | hosted | MANUAL (param `templateBranch`) | central `build-java` from `main` / `master` / `staging/preprod` / `staging/release-hardening` | team-quant | 2026-02-28 succeeded | 5 (8.5) | **Migrate** (as `workflow_dispatch`; retire once template branches are consolidated) |
| 104 | risk-batch-ci | `services/risk-batch/azure-pipelines.yml` | Python 3.11 | hosted | CI `main` | central `build-python`, `run-tests`, `release-standard` (**`staging/preprod`**) | team-quant | 2026-03-15 succeeded | 38 (13.7) | **Migrate** |
| 105 | risk-batch-legacy | `services/risk-batch/azure-pipelines-legacy.yml` | Python 3.9 | hosted (`ubuntu-20.04`) | MANUAL — "still triggered externally by downstream jobs" | legacy `build-python-legacy` (**`legacy/master-support`**) | team-quant (last modified by contractor) | 2026-01-10 succeeded | 2 (8.7) | **Dead** — retire after the external trigger is identified |
| 106 | frontend-workbench-ci | `services/frontend-workbench/azure-pipelines.yml` | Node 18 / React (SSR) | hosted | CI `main`, `feature/*` | alt `frontend-build`, `frontend-deploy`×2 (**`team/frontend-custom`**) | team-frontend | 2026-03-16 succeeded | 62 (12.3) | **Migrate** |
| 107 | regulatory-reporting-ci | `services/regulatory-reporting/azure-pipelines.yml` | Python 3.11 | hosted | CI `main` **and** SCHED weekdays 06:00 UTC | alt `team-build-custom` (**`team/reporting-hotfix`**) + inline report generation | team-reporting | 2026-03-17 succeeded | 65 (82.4) | **Do not migrate** (compliance workflow disguised as a build — see §4) |
| 108 | market-sim-ci | `services/market-sim/azure-pipelines.yml` | Rust | hosted | CI `main` | none (inline) | ⚠ team-quant? (docs "low confidence") | 2026-03-08 succeeded | 18 (23.4) | **Migrate** |
| 109 | ops-control-plane-ci | `services/ops-control-plane/azure-pipelines.yml` | Go 1.22 | hosted | CI `main` | none (inline; predates central `build-go`) | platform-team | 2026-03-13 succeeded | 25 (7.8) | **Migrate** |
| 110 | notebook-executor-nightly | `services/notebook-executor/azure-pipelines.yml` | Python 3.10 / Jupyter | **linux-build-workers** (self-hosted) | SCHED daily 02:00 UTC | none (inline) | ⚠ unknown | 2026-03-17 **partiallySucceeded** (18/90 partial) | 90 (165.2) | **Do not migrate** — non-build |
| 111 | scenario-runner-weekly | `services/scenario-runner/azure-pipelines.yml` | Python 3.11 | **high-memory-pool** (self-hosted, 128 GB) | SCHED Fri 22:00 UTC + MANUAL params | none (inline) | ⚠ unknown | 2026-03-15 succeeded | 13 (228.1) | **Do not migrate** — non-build |
| 112 | var-scenario-sweep-nightly | `night-jobs/compute/var-scenario-sweep.yml` | Python 3.11 | **high-memory-pool** | SCHED weeknights 01:00 UTC | none (inline) | team-quant (docs say "team-quant?") | 2026-03-17 succeeded | 65 (172.2) | **Do not migrate** — non-build |
| 113 | daily-positions-export | `night-jobs/business/daily-positions-export.yml` | Python 3.11 / pyodbc | **linux-build-workers** | SCHED weekdays 23:00 UTC | none (inline) | team-reporting (docs say "team-reporting?") | 2026-03-17 succeeded | 65 (75.5) | **Do not migrate** — non-build |
| 114 | attestation-backfill-weekly | `night-jobs/compliance/attestation-backfill.yml` | Python 3.11 | **linux-build-workers** | SCHED Sun 03:00 UTC | none (inline; calls `build-tools/compliance/generate_metadata.py`) | shared-ci-platform (docs say "shared-ci-platform?") | 2026-03-16 succeeded | 13 (93.3) | **Do not migrate** — non-build |
| 115 | bulk-reprocess-trades | `adhoc/bulk-reprocess-trades.yml` | Python 3.11 | hosted | MANUAL (date-range params) | none (inline) | ⚠ unknown | 2026-02-25 succeeded | 3 (325.1) | **Do not migrate** — non-build ad-hoc job |
| 116 | onetime-data-migration | `adhoc/onetime-data-migration.yml` | Python 3.11 / pyodbc | hosted | MANUAL; **paused in ADO** | none (inline) | ⚠ unknown | 2024-08-20 succeeded (1 run ever) | 0 | **Dead** — delete |
| 117 | old-pricing-pipeline | `deprecated/old-pricing-pipeline.yml` | .NET 6 | hosted (`ubuntu-20.04`) | MANUAL; **disabled in ADO** | resources ref **`legacy/master-support`** (no template actually consumed) | ⚠ none | 2023-06-15 succeeded | 0 | **Dead** — delete (replaced by 101) |
| 118 | batch-runner-v1 | `deprecated/batch-runner-v1.yml` | Python 3.8 | hosted (`ubuntu-20.04`) | MANUAL; **disabled in ADO** | none (inline) | ⚠ none | 2023-02-01 **failed** | 0 | **Dead** — delete (replaced by 104 + night-jobs) |
| — | *(not registered in ADO)* | `archive/old-release-workflow.yml` | n/a (echo stub) | hosted (`ubuntu-20.04`) | MANUAL | none | none | never (archived Q3 2022) | 0 | **Dead** — delete |

Not pipelines (excluded from the count, but in scope as dependencies): 16 files under `templates/`, 7 under `alt-templates/`, 3 under `build-tools/{yaml,release}/`, and `services/risk-batch/pipeline-fragments/build-python-local.yml` (a service-local fork **not referenced by any pipeline** — dead template). `upstream-reference/` is vendored Microsoft sample YAML with no ADO definitions and is out of scope.

## 3. Migrate — build pipelines (7)

All seven run on the hosted `Azure Pipelines` pool → `ubuntu-latest` GitHub-hosted runners with no infrastructure change. Per-pipeline notes:

| Pipeline | What must be reproduced | Migration blockers / gotchas |
|---|---|---|
| **pricing-engine-ci (101)** | `UseDotNet@2` 8.0.x → restore/build/test (`XPlat Code Coverage`)/publish; JUnit normalisation via `run-tests.yml`; deploy to `dev` env with `requireApproval: true`. | Template chain calls `publish_artifact.py --registry Artifactory`, `notify_release_orchestrator.py` (D2) and `generate_attestation.py` on every `main` build. **No owner** — nobody can sign off on behavioural parity. Uses variable groups `shared-ci-secrets`, `artifact-registry-credentials`; service connection `AzureSubscription-Dev`. |
| **portfolio-api-ci (102)** | `JavaToolInstaller@0` 17 + `Maven@4 package`; deploy to `staging` env (1 approver: shared-ci-platform-team). | Consumes templates from **`master`**, which is not in this repo — parity assumed equal to `main`. CI trigger also fires on `master` source branch (dead branch). Same Artifactory/D2/attestation coupling as 101. |
| **portfolio-api-canary (103)** | Manual, parameterised build-only pipeline used to A/B template branches. | Its entire purpose is exercising 4 template branches; 3 of them are unavailable here. Migrate as a `workflow_dispatch` reusable-workflow smoke test, then **retire after template consolidation**. No release stage, no downstream writes. |
| **risk-batch-ci (104)** | `build-python.yml` (flake8/black, pytest + cov, sdist/wheel) + `run-tests.yml` + deploy to `dev`. | Depends on retry logic that exists only on **`staging/preprod`** (per docs/API notes); `main`'s `build-python.yml` has no retry → migrating from `main` silently drops behaviour. Uses non-shared VG `risk-batch-config` (`RISK_DB_CONNECTION_STRING` secret). `pipeline-fragments/build-python-local.yml` is an unreferenced fallback fork — delete, don't port. |
| **frontend-workbench-ci (106)** | `frontend-build.yml` (npm ci, lint, `build:react`, `build:ssr`, jest --coverage, zip) then `frontend-deploy.yml` to `dev-frontend` and `staging-frontend` (1 approver: team-frontend). | Templates come from **`team/frontend-custom`**; the copy on `main` may differ. YAML comment records a **known regression**: the main-branch-only guard on the staging deploy was lost. CDN purge + storage upload use VG `frontend-cdn-config` (2 secrets) and service connections `AzureSubscription-Dev/Staging`. Triggers on `feature/*` — the last run was on `feature/dark-mode`. |
| **market-sim-ci (108)** | Inline rustup + `cargo clippy -D warnings`, `cargo build --release`, `cargo test --test-threads=1`, publish binary; Deploy stage on `main` only. | Deploy step is an `echo` that explicitly says it is "managed outside D2" → no release-orchestrator record exists for this service; ADO lists `ContainerRegistry-ACR` as used but the YAML never pushes an image. Owner "team-quant?" is low confidence. |
| **ops-control-plane-ci (109)** | `GoTool@0` 1.22, `go mod download/verify`, `go vet`, `go test -coverprofile`, static `CGO_ENABLED=0` build, publish binary. | Cleanest candidate. ADO attaches VG `ops-infra-credentials` (K8s token) and `ContainerRegistry-ACR` but the YAML has **no deploy/push step** — either the credentials are unused (remove) or a deploy exists outside this YAML (find it). Should adopt central `build-go.yml` equivalent rather than porting inline steps verbatim. |

## 4. Do not migrate — non-build workloads (7)

These use ADO as a scheduler/compute grid. Recommendation: **leave on ADO until re-platformed** onto a proper job runner (K8s CronJob / Azure Container Apps Jobs / AWS Batch / Airflow) in the same network segment as the self-hosted pools, then decommission the ADO definitions. Do not convert to GHA `schedule:` workflows.

| Pipeline | Why it is not a build | Runtime constraints that rule out GitHub-hosted runners | Internal dependencies |
|---|---|---|---|
| **regulatory-reporting-ci (107)** | `ComplianceBuild` stage produces a `regulatory-compliance-pkg` wheel, but the real work is `GenerateReports`: runs `generate_reports.py`, uploads compliance metadata and a **prod** attestation to attestation-database. YAML header: "does NOT produce a deployable artifact". Avg 82 min, runs 65×/90d — almost entirely from the weekday 06:00 schedule, not code changes. 365-day retention for audit. | Hosted pool today, so *technically* portable — but it targets the `prod` environment (2 approvers + business hours + exclusive lock) and writes audit records; moving it changes the audit trail. | VGs `compliance-store-credentials`, `regulatory-reporting-config` (DB conn string, SMTP, distribution list); `AzureSubscription-Prod`; attestation-database. **Source (`services/regulatory-reporting/src`, `requirements.txt`) is not in the repo.** Recommended split: lint/test of the package → GHA; scheduled report run → job platform. |
| **notebook-executor-nightly (110)** | Runs every `*.ipynb` with papermill, converts to HTML, publishes outputs. Failures only emit warnings (`partiallySucceeded` 18/90). | 180-min job timeout (150 min for execution step); `linux-build-workers` demanded for `python3`, conda, Jupyter and network to compliance-store/positions-db/data-warehouse. | VG `internal-network-credentials`. **No owner**; last modified by `unknown-service-account`. `services/notebook-executor/notebooks/` **does not exist in the repo** — the notebooks being executed nightly are unknown. |
| **scenario-runner-weekly (111)** | Monte Carlo simulations (`run_scenarios.py`, `aggregate_results.py`), parameterised count/model/format. | 360-min timeout (exceeds GHA 6h job limit with no headroom); needs 128 GB/32-core `high-memory-pool` + `compute-cluster` network. | VG `internal-network-credentials`. **No owner**. `services/scenario-runner/src/` **not in repo**. |
| **var-scenario-sweep-nightly (112)** | 50,000-scenario VaR sweep, uploads to data-warehouse (`risk_analytics` schema). | 240-min timeout; `high-memory-pool`; writes to `/tmp/var-results/` on a persistent agent. | VGs `internal-network-credentials`, `data-warehouse-credentials`. Owner team-quant (API) vs "team-quant?" (docs). |
| **daily-positions-export (113)** | Extract positions via pyodbc → parquet, Excel summary, `distribute_report.py` to team-reporting/team-quant (SMTP). Business reporting job. | 120-min timeout; needs `positions-db` + `internal-smtp` reachability. | VGs `internal-network-credentials`, `positions-db-credentials`. Downstream reporting systems consume the export — **consumer list unknown**. |
| **attestation-backfill-weekly (114)** | Scans attestation-database for gaps, regenerates records with `--dry-run false`, records its own metadata. Compliance automation. | 180-min timeout; `compliance-store` network. | VG `compliance-store-credentials`. Owner shared-ci-platform (API) vs "?" (docs). Coupled to the attestation schema written by the build pipelines' `generate_attestation.py` — if that format changes during migration, backfill breaks. |
| **bulk-reprocess-trades (115)** | Ad-hoc trade reprocessing over a date range (`reprocess_trades.py`). | **480-min timeout — exceeds GHA's 6-hour job limit**; avg run 325 min. Runs on hosted pool but is attached to `internal-network-credentials`, implying it reaches internal systems from a hosted agent (egress/allow-list dependency to verify). | **No owner**; `adhoc/scripts/reprocess_trades.py` **not in repo**. 3 runs in 90d — still in active use. |

## 5. Dead pipelines (5)

| Pipeline | Evidence | Action |
|---|---|---|
| **risk-batch-legacy (105)** | `trigger: none`; 2 runs in 90d, last 2026-01-10; Python 3.9 + `unittest` on `ubuntu-20.04` (image no longer offered on hosted agents); uses frozen `legacy/master-support`. ADO note: "still triggered externally by downstream jobs". | **Retire.** Blocker: identify the external caller (check ADO build queue `requestedFor`/`reason` on runs 20260110.1 and prior). Point it at `risk-batch-ci` output (`risk-batch-dist`) and delete. The artifact name differs (`risk-batch-legacy`) — any consumer keyed on that name breaks. |
| **onetime-data-migration (116)** | `queueStatus: paused`; exactly 1 run (2024-08-20); YAML header: "should have been deleted". Holds `positions-db-credentials` (2 secrets). | **Delete** definition, YAML, and revoke its VG binding. |
| **old-pricing-pipeline (117)** | `queueStatus: disabled`; 0 runs in 90d, last 2023-06; header "DO NOT ENABLE"; superseded by 101. | **Delete.** Only remaining reference to `legacy/master-support` besides 105. |
| **batch-runner-v1 (118)** | `queueStatus: disabled`; last run 2023-02 **failed**; Python 3.8 (EOL); superseded by 104 + 112. | **Delete.** |
| **archive/old-release-workflow.yml** | Not registered in ADO at all; body is a single `echo`. | **Delete** along with `archive/`. |

Also dead (templates, not pipelines): `services/risk-batch/pipeline-fragments/build-python-local.yml` (zero consumers), `templates/legacy/release-old.yml` (zero consumers on `main`), `templates/release/release-hotfix.yml`, `release-preprod.yml`, `release-prod.yml` (zero consumers on `main`; `preprod` environment has `_pipelinesUsing: []`). Consumers may exist on the missing branches — verify before deleting.

## 6. Ownership gaps

| Pipeline(s) | ADO `owner_team` | `docs/ownership-gaps.md` | Risk |
|---|---|---|---|
| pricing-engine-ci (101) | unknown | unknown / low | Production service build with a `dev` release gate (`requireApproval: true`) and no approver who understands it. Last modified by a departed contractor account. **Must be assigned before migration** — there is nobody to sign off parity, and any future promotion to `prod` needs a `service-owner` approver per that environment's checks. |
| market-sim-ci (108) | team-quant | team-quant? / low | Deploys outside D2; if team-quant disowns it there is no deployment record anywhere. |
| notebook-executor-nightly (110) | unknown | ? / none | Runs nightly on internal infra with internal credentials; nobody claims it; notebooks not in repo. Highest risk item in the estate — recommend a **disable-and-see-who-shouts** window before re-platforming. |
| scenario-runner-weekly (111) | unknown | ? / none | 6-hour weekly runs on the most expensive pool; no owner to validate outputs. |
| bulk-reprocess-trades (115) | unknown | unknown | Mutates trade data; run by `unknown-service-account`; 8-hour window. |
| onetime-data-migration (116) | unknown | unknown | Dead; just needs deletion approval. |
| old-pricing-pipeline (117), batch-runner-v1 (118) | none | — | Dead; deletion only. |
| var-scenario-sweep (112), daily-positions-export (113), attestation-backfill (114) | team-quant / team-reporting / shared-ci-platform | all marked "?" | **Docs and API disagree** — treat as unconfirmed until each team acknowledges in writing. |
| risk-batch-legacy (105) | team-quant | — | Owner known, but the *downstream consumer* that triggers it is not. |

Accounts appearing as `last_modified_by` that are not people: `contractor-account@contoso.com` (101, 105, 117, 118), `unknown-service-account@contoso.com` (110, 111, 115, 116). Any pipeline last touched by these has effectively no maintainer.

## 7. Downstream-tooling and platform-coupling risks

### 7.1 Integrations hidden inside shared templates

| Integration | Invoked by | Pipelines affected | Migration risk |
|---|---|---|---|
| **Artifactory** (`build-tools/scripts/publish_artifact.py --registry Artifactory`) | `build-dotnet.yml`, `build-java.yml`, `build-python.yml`, `publish-helpers.yml` | 101, 102, 104 (via VG `artifact-registry-credentials`) | Every GHA build must keep registering artifacts or downstream promotion breaks. `build-node/go/rust.yml` do *not* register → 106/108/109 have no Artifactory record today (inconsistency to decide on, not replicate blindly). |
| **D2 release orchestrator** (`notify_release_orchestrator.py`) | `release-standard.yml`, `release-prod.yml`, `build-tools/release/release-notify.yml` | 101 (dev), 102 (staging), 104 (dev) | D2 expects a deployment event per env; GHA `environment:` deployments must emit the same payload (`--service --env --build-id --status`). `Build.BuildId` has no direct GHA equivalent — decide whether D2 keys on `run_id` or `run_number`. market-sim (108) intentionally bypasses D2. |
| **attestation-database** (`generate_attestation.py`, `compliance/generate_metadata.py`) | `release-standard.yml`, `release-hotfix.yml`, `publish-helpers.yml`, `team-build-custom.yml`, inline in 107 & 114 | 101, 102, 104, 107, 114 | Compliance audit trail. `release-prod.yml` *reads* attestation-database before prod deploys, and 114 backfills it. Changing the record shape or `build-id` semantics mid-migration breaks prod gating and the backfill job. Recommend attestation records carry both ADO and GHA identifiers during the parallel-run period. |
| **compare_build_outputs.py against `validation/baselines/`** | `release-prod.yml` | none on `main` | Baselines already exist for the 6 build services (observed from real ADO runs) and are consumed by `.github/workflows/validate-migration.yml`. Keep them in sync with the GHA runs, not the other way round. |

### 7.2 ADO-only configuration that has no YAML footprint

| Object | Items | Pipelines | GHA mapping |
|---|---|---|---|
| Variable groups | 10 groups (API `count` says 9 — one group is unaccounted for in the header), 14 secret values | all except 108, 117, 118 | Org/repo/environment secrets. Shared groups (`shared-ci-secrets`: NuGet/PyPI/npm feed + tokens) → org secrets; non-shared → environment secrets. `internal-network-credentials` and `positions-db-credentials` are bound only to non-build workloads — **do not copy them into GitHub**. |
| Service connections | 5 (3× `azurerm` SP-key, 1 ACR, 1 GitHub PAT) | 101,102,104,106,107 (Azure); 108,109 (ACR) | Prefer OIDC federated credentials over copying SP keys. `GitHub-SourceMirror` has zero consumers → delete. ACR bindings on 108/109 are unused by their YAML → verify before recreating. |
| Environments & checks | `dev` (none), `staging` (1 approver), `preprod` (2 approvers + business hours, **unused**), `prod` (2 approvers + business hours Mon–Thu + exclusive lock), `dev-frontend` (none), `staging-frontend` (1 approver) | 101,102,104,106,107 | GitHub Environments support required reviewers and (Enterprise) deployment branch policies, but **not business-hours windows or exclusive locks natively** — need `concurrency:` groups for the lock and a custom deployment-protection rule or scheduled gate for business hours. |
| Retention | 30 days / min 5 (builds); **365 days** (107, 114) | | GHA artifact retention max is 90 days at the org level — 365-day audit retention for 107/114 requires external archival regardless of where they run. |
| Agent pools | `Azure Pipelines` (hosted), `linux-build-workers` (8, 2 offline), `high-memory-pool` (4), `windows-build-workers` (legacy, 1 of 2 offline, **zero consumers**) | | Hosted → `ubuntu-latest`. Self-hosted pools stay with the non-build workloads. `windows-build-workers` is a decommission candidate now; the ADO note warns a pipeline could select it via a UI-level pool override not visible in YAML — check each definition's `queue` (all 18 report a different pool, so none do). |
| `ubuntu-20.04` image | 105, 117, 118, archive | | Image no longer offered on either platform's hosted runners; all four are dead pipelines, no action beyond deletion. |

### 7.3 Template-branch drift (unverifiable from this repo)

| Branch | Consumers | Exists on `origin`? | Claimed divergence | Risk |
|---|---|---|---|---|
| `main` | 101, 103 | yes | canonical | — |
| `master` | 102, 103 | **no** | "small divergences" | 102 may be building with older `build-java`/`release-standard` than what is analysed here. |
| `staging/preprod` | 104, 103 | **no** | retry logic in `build-python.yml` | Porting from `main` drops the retry; test flakiness would surface as new failures in GHA. |
| `staging/release-hardening` | 103 only | **no** | extra release gates | Unknown consumers per docs; only the canary touches it. Safe to drop with 103. |
| `team/frontend-custom` | 106 | **no** | SSR + webpack config | `alt-templates/frontend/*` on `main` may lag the branch team-frontend actually runs. |
| `team/quant-experiments` | none in YAML | **no** | "possibly scenario-runner, notebook-executor" | Both named consumers are fully inline on `main`, so no YAML here references it — but the branch itself is unavailable and `docs/branch-usage-notes.md` still lists them as possible consumers. Export and check before deleting. |
| `team/reporting-hotfix` | 107 | **no** | extra compliance metadata steps | `team-build-custom.yml` on `main` already contains `generate_metadata.py`; branch may add more. |
| `legacy/master-support` | 105, 117 | **no** | frozen | Both consumers are dead → delete branch with them. |

Action: export these seven branches from the ADO `shared-ci-platform` repo (or confirm they were never mirrored) and diff `templates/` and `alt-templates/` against `main` before any "Migrate" pipeline is declared equivalent. The existing `validate-migration.yml` parity harness compares run conclusions, test counts and artifact names between ADO and GHA; it does not cover deployment side effects, downstream writes (Artifactory/D2/attestation) or artifact contents, so it cannot substitute for reviewing the templates themselves.

### 7.4 Source referenced by pipelines but absent from the repo

| Pipeline | Missing path |
|---|---|
| 107 regulatory-reporting-ci | `services/regulatory-reporting/requirements.txt`, `src/generate_reports.py` |
| 110 notebook-executor-nightly | `services/notebook-executor/notebooks/` |
| 111 scenario-runner-weekly | `services/scenario-runner/src/run_scenarios.py`, `aggregate_results.py` |
| 115 bulk-reprocess-trades | `adhoc/scripts/reprocess_trades.py` |
| 116 onetime-data-migration | `adhoc/scripts/migrate_data.py` |
| 118 batch-runner-v1 | `requirements.txt`, `setup.py`, `batch_runner/`, `config/batch-config.yaml` (relative to repo root) |

Either these live in another repo checked out by an ADO-side resource not captured in YAML, or the pipelines are running against code that only exists on the self-hosted agents. Both possibilities need confirmation before any of them is re-platformed.

## 8. Recommended sequencing

1. **Ownership first** — assign 101, 108, 110, 111, 115 and get written confirmation for 112/113/114. Nothing else should be signed off without an owner.
2. **Delete dead pipelines** (116, 117, 118, archive) immediately; retire 105 once its external trigger is found. Remove `legacy/master-support`, `windows-build-workers`, `GitHub-SourceMirror`, and the `preprod` environment in the same sweep. Hold `team/quant-experiments` until it is exported and its history checked — `docs/branch-usage-notes.md` names scenario-runner/notebook-executor as possible consumers even though neither YAML on `main` references it.
3. **Recover the template branches** from ADO and diff against `main`; fold the retry logic (`staging/preprod`) and SSR steps (`team/frontend-custom`) into `main` so there is one template lineage to migrate.
4. **Migrate builds** in order of coupling: 109 → 108 → 103 → 106 → 102 → 104 → 101, running each in parallel with ADO under `validate-migration.yml` until parity holds. Reproduce Artifactory/D2/attestation calls as composite actions before the first release-stage migration.
5. **Re-platform non-build workloads** (110–115, 107's report stage) onto a job scheduler with internal network access; keep them on ADO until then. Do not convert them to `schedule:` workflows.
6. **Decommission ADO** only after 107's audit retention and 114's backfill have a home outside both platforms.
