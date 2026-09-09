# Pipeline Inventory & Classification Report

**Organization:** contoso-financial  
**Project:** shared-ci-platform  
**API Data Date:** 2026-03-17  
**Report Generated:** 2026-05-12  
**Scope:** Full inventory of 18 ADO pipeline definitions, 9 variable groups, 5 service connections, 6 environments, 4 agent pools, and 8 long-lived branches.

---

## 1. Pipeline Inventory Table

| # | Pipeline Name | ADO ID | YAML Path | Queue Status | Pool | Last Run Date | Last Result | 90-Day Runs | Avg Duration | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pricing-engine-ci | 101 | `services/pricing-engine/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-14 | succeeded | 47 | 7.5 min | unknown |
| 2 | portfolio-api-ci | 102 | `services/portfolio-api/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-12 | succeeded | 31 | 9.8 min | team-quant |
| 3 | portfolio-api-canary | 103 | `services/portfolio-api/azure-pipelines-canary.yml` | **enabled** | Azure Pipelines (hosted) | 2026-02-28 | succeeded | 5 | 8.5 min | team-quant |
| 4 | risk-batch-ci | 104 | `services/risk-batch/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-15 | succeeded | 38 | 13.7 min | team-quant |
| 5 | risk-batch-legacy | 105 | `services/risk-batch/azure-pipelines-legacy.yml` | **enabled** | Azure Pipelines (hosted) | 2026-01-10 | succeeded | 2 | 8.7 min | team-quant |
| 6 | frontend-workbench-ci | 106 | `services/frontend-workbench/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-16 | succeeded | 62 | 12.3 min | team-frontend |
| 7 | regulatory-reporting-ci | 107 | `services/regulatory-reporting/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-17 | succeeded | 65 | 82.4 min | team-reporting |
| 8 | market-sim-ci | 108 | `services/market-sim/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-08 | succeeded | 18 | 23.4 min | team-quant |
| 9 | ops-control-plane-ci | 109 | `services/ops-control-plane/azure-pipelines.yml` | **enabled** | Azure Pipelines (hosted) | 2026-03-13 | succeeded | 25 | 7.8 min | platform-team |
| 10 | notebook-executor-nightly | 110 | `services/notebook-executor/azure-pipelines.yml` | **enabled** | linux-build-workers (self-hosted) | 2026-03-17 | partiallySucceeded | 90 | 165.2 min | **unknown** |
| 11 | scenario-runner-weekly | 111 | `services/scenario-runner/azure-pipelines.yml` | **enabled** | high-memory-pool (self-hosted) | 2026-03-14 | succeeded | 13 | 228.1 min | **unknown** |
| 12 | var-scenario-sweep-nightly | 112 | `night-jobs/compute/var-scenario-sweep.yml` | **enabled** | high-memory-pool (self-hosted) | 2026-03-17 | succeeded | 65 | 172.2 min | team-quant |
| 13 | daily-positions-export | 113 | `night-jobs/business/daily-positions-export.yml` | **enabled** | linux-build-workers (self-hosted) | 2026-03-16 | succeeded | 65 | 75.5 min | team-reporting |
| 14 | attestation-backfill-weekly | 114 | `night-jobs/compliance/attestation-backfill.yml` | **enabled** | linux-build-workers (self-hosted) | 2026-03-16 | succeeded | 13 | 93.3 min | shared-ci-platform |
| 15 | bulk-reprocess-trades | 115 | `adhoc/bulk-reprocess-trades.yml` | **enabled** | Azure Pipelines (hosted) | 2026-02-25 | succeeded | 3 | 325.1 min | **unknown** |
| 16 | onetime-data-migration | 116 | `adhoc/onetime-data-migration.yml` | **paused** | Azure Pipelines (hosted) | 2024-08-20 | succeeded | 1 | 222.8 min | **unknown** |
| 17 | old-pricing-pipeline | 117 | `deprecated/old-pricing-pipeline.yml` | **disabled** | Azure Pipelines (hosted) | 2023-06-15 | succeeded | 0 | — | none |
| 18 | batch-runner-v1 | 118 | `deprecated/batch-runner-v1.yml` | **disabled** | Azure Pipelines (hosted) | 2023-02-01 | failed | 0 | — | none |

### Dead Pipelines (Skip in Migration)

These pipelines have 0 runs in the last 90 days AND are disabled/paused:

| Pipeline | ADO ID | Status | Last Run | Reason |
|---|---|---|---|---|
| old-pricing-pipeline | 117 | **disabled** | 2023-06-15 | Replaced by pricing-engine-ci (ID 101). Last run 33 months ago. |
| batch-runner-v1 | 118 | **disabled** | 2023-02-01 | Replaced by risk-batch-ci + night-jobs. Last run failed 39 months ago. |
| onetime-data-migration | 116 | **paused** | 2024-08-20 | One-time migration completed Aug 2024. Should have been deleted. 1 total run ever. |

**Recommendation:** These 3 pipelines can be excluded from migration planning entirely. Archive in ADO and do not recreate in GitHub Actions.

---

## 2. Pipeline Classification

### Category 1: Central Template Consumers (4 pipelines)
Pipelines that use `templates/build/` or `templates/release/` from a shared branch.

| Pipeline | Template Branch | Templates Used |
|---|---|---|
| pricing-engine-ci (101) | `main` | `build-dotnet.yml`, `run-tests.yml`, `release-standard.yml` |
| portfolio-api-ci (102) | `master` ⚠️ | `build-java.yml`, `release-standard.yml` |
| risk-batch-ci (104) | `staging/preprod` ⚠️ | `build-python.yml`, `run-tests.yml`, `release-standard.yml` |
| risk-batch-legacy (105) | `legacy/master-support` ⚠️ | `build-python-legacy.yml` |

### Category 2: Alt-Template Consumers (1 pipeline)
Pipelines that use team-maintained alternative templates.

| Pipeline | Template Branch | Templates Used |
|---|---|---|
| frontend-workbench-ci (106) | `team/frontend-custom` | `frontend-build.yml`, `frontend-deploy.yml` |

### Category 3: Hybrid (1 pipeline)
Pipelines mixing team-override templates with inline steps.

| Pipeline | Template Branch | Templates Used | Notes |
|---|---|---|---|
| regulatory-reporting-ci (107) | `team/reporting-hotfix` | `team-build-custom.yml` | Looks like a build but is actually a compliance workflow. 82-min avg runs. |

### Category 4: Custom Inline (2 pipelines)
Pipelines with fully inline YAML, no shared templates.

| Pipeline | Stack | Notes |
|---|---|---|
| market-sim-ci (108) | Rust | Custom Rust pipeline. Central `build-rust.yml` exists but was added after this pipeline. |
| ops-control-plane-ci (109) | Go | Custom Go pipeline. Central `build-go.yml` exists but was never adopted. |

### Category 5: Non-Build Workloads (5 pipelines)
Pipelines abusing CI infrastructure for compute/data/compliance jobs.

| Pipeline | Schedule | Pool | Workload Type |
|---|---|---|---|
| notebook-executor-nightly (110) | Daily 02:00 UTC | linux-build-workers | Jupyter notebook execution |
| scenario-runner-weekly (111) | Fri 22:00 UTC | high-memory-pool | Monte Carlo simulations |
| var-scenario-sweep-nightly (112) | Weekdays 01:00 UTC | high-memory-pool | VaR scenario calculations (50K) |
| daily-positions-export (113) | Weekdays 23:00 UTC | linux-build-workers | Data export + Excel reports |
| attestation-backfill-weekly (114) | Sun 03:00 UTC | linux-build-workers | Compliance attestation backfill |

### Category 6: Ad-Hoc / Deprecated (3 pipelines)
Manual or stale pipelines.

| Pipeline | Status | Last Run | Notes |
|---|---|---|---|
| bulk-reprocess-trades (115) | enabled | 2026-02-25 | Manual trigger. 8-hour timeout. |
| onetime-data-migration (116) | **paused** 🔴 | 2024-08-20 | **DEAD.** Delete candidate. |
| old-pricing-pipeline (117) | **disabled** 🔴 | 2023-06-15 | **DEAD.** Replaced by ID 101. |
| batch-runner-v1 (118) | **disabled** 🔴 | 2023-02-01 | **DEAD.** Replaced by risk-batch + night-jobs. |

---

## 3. Template Dependency Map

### Branch → Template → Pipeline Consumption

```
main
├── templates/build/build-dotnet.yml ──────── pricing-engine-ci (101)
├── templates/build/build-java.yml ────────── portfolio-api-canary (103) [when param=main]
├── templates/test/run-tests.yml ──────────── pricing-engine-ci (101)
└── templates/release/release-standard.yml ── pricing-engine-ci (101)

master (legacy)
├── templates/build/build-dotnet.yml ──────── [.NET 6.0.x, older review date]
├── templates/build/build-python.yml ─────── [Python 3.10, linting disabled, older]
├── templates/build/build-java.yml ────────── portfolio-api-ci (102)
└── templates/release/release-standard.yml ── portfolio-api-ci (102)

staging/preprod
├── templates/build/build-python.yml ─────── risk-batch-ci (104) [retry logic + testRetryCount param]
└──                                           portfolio-api-canary (103) [when param=staging/preprod]

staging/release-hardening
└── templates/release/release-standard.yml ── portfolio-api-canary (103) [when param=staging/release-hardening]
                                              [pre-deploy validation + health checks added]

team/frontend-custom
├── alt-templates/frontend/frontend-build.yml ── frontend-workbench-ci (106) [Lighthouse CI + build ID suffix]
├── templates/build/build-node.yml ────────────── [SSR + Storybook params, Node 18.x default]
└──                                                [No direct consumer of modified build-node.yml from this branch]

team/quant-experiments
└── templates/build/build-python.yml ─────── [conda support, GPU pool, extended timeouts]
                                              No confirmed active consumer

team/reporting-hotfix
└── alt-templates/team-overrides/team-build-custom.yml ── regulatory-reporting-ci (107)
                                                          [audit trail logging + pre-build validation]

legacy/master-support (FROZEN)
├── templates/build/build-dotnet.yml ──────── [.NET 6.0.x, FROZEN banner]
├── templates/build/build-python.yml ─────── [Python 3.8, linting disabled, FROZEN]
├── templates/legacy/build-python-legacy.yml ── risk-batch-legacy (105)
└──                                              old-pricing-pipeline (117, disabled)
```

### Template Not Referenced by Any Pipeline
| Template | Location | Notes |
|---|---|---|
| `templates/build/build-rust.yml` | `templates/build/` | Exists but market-sim uses inline Rust. |
| `templates/build/build-go.yml` | `templates/build/` | Exists but ops-control-plane uses inline Go. |
| `templates/build/build-node.yml` | `templates/build/` (main) | frontend-workbench uses the `team/frontend-custom` branch version instead. |
| `templates/release/release-hotfix.yml` | `templates/release/` | No pipeline references this template. |
| `templates/release/release-preprod.yml` | `templates/release/` | No pipeline references this template. |
| `templates/release/release-prod.yml` | `templates/release/` | No pipeline references this template. |
| `templates/legacy/release-old.yml` | `templates/legacy/` | No pipeline references this template. |
| `alt-templates/data-science/build-python.yml` | `alt-templates/data-science/` | No pipeline references this template. |
| `alt-templates/data-science/ds-model-build.yml` | `alt-templates/data-science/` | No pipeline references this template. |
| `alt-templates/data-science/notebook-package-build.yml` | `alt-templates/data-science/` | No pipeline references this template. |
| `alt-templates/data-science/python-batch.yml` | `alt-templates/data-science/` | No pipeline references this template. |
| `services/risk-batch/pipeline-fragments/build-python-local.yml` | Local fork | Not currently referenced; exists as fallback. |

---

## 4. Non-Build Workload Analysis

All 7 identified non-build workloads that are abusing CI infrastructure as compute:

### 4.1 Jupyter Notebook Execution — `notebook-executor-nightly` (ID 110)
- **Schedule:** Daily at 02:00 UTC (every day including weekends)
- **Pool:** `linux-build-workers` (self-hosted, 16GB RAM, 4 cores)
- **Timeout:** 180 minutes (inner step: 150 min)
- **What it does:** Runs all `*.ipynb` files in `services/notebook-executor/notebooks/` via `papermill`, converts outputs to HTML
- **Dependencies:** numpy, pandas, scipy, scikit-learn, matplotlib, seaborn, jupyter, papermill
- **Network:** Requires internal network access
- **Owner:** **Unknown** — no owner identified
- **Health:** 90 runs in 90 days; 72 succeeded, 18 partially succeeded, 0 failed
- **Migration target:** Should NOT be a GHA workflow. Migrate to a scheduled compute platform (Kubernetes CronJob, Azure Container Instances, AWS Batch).

### 4.2 Monte Carlo Simulations — `scenario-runner-weekly` (ID 111)
- **Schedule:** Friday 22:00 UTC + manual with custom parameters
- **Pool:** `high-memory-pool` (self-hosted, 128GB RAM, 32 cores)
- **Timeout:** 360 minutes (inner step: 300 min)
- **What it does:** Parameterized Monte Carlo simulations (default: 10K scenarios, v2.3 model, parquet output)
- **Dependencies:** numpy, pandas, scipy, pyarrow
- **Network:** Requires internal network + compute cluster access
- **Owner:** **Unknown** — likely team-quant
- **Health:** 13 runs in 90 days; 11 succeeded, 2 failed
- **Migration target:** NOT GHA. Move to dedicated compute (K8s jobs, AWS Batch, Azure Container Instances).

### 4.3 VaR Scenario Sweep — `var-scenario-sweep-nightly` (ID 112)
- **Schedule:** Weekdays at 01:00 UTC
- **Pool:** `high-memory-pool` (self-hosted, 128GB RAM, 32 cores)
- **Timeout:** 240 minutes (inner step: 200 min)
- **What it does:** 50,000 VaR scenarios at 95/99/99.9% confidence levels, uploads to data warehouse
- **Dependencies:** numpy, pandas, scipy, pyarrow, requests
- **Network:** Requires internal network + data warehouse access
- **Owner:** team-quant
- **Health:** 65 runs in 90 days; 60 succeeded, 5 failed
- **Migration target:** NOT GHA. Move to dedicated compute.

### 4.4 Daily Positions Export — `daily-positions-export` (ID 113)
- **Schedule:** Weekdays at 23:00 UTC (7 PM ET)
- **Pool:** `linux-build-workers` (self-hosted, 16GB RAM, 4 cores)
- **Timeout:** 120 minutes (inner step: 60 min)
- **What it does:** Extracts positions data via pyodbc, generates Excel summaries, distributes to team-reporting and team-quant
- **Dependencies:** pandas, pyodbc, sqlalchemy, openpyxl, requests
- **Network:** Requires internal network + positions DB access
- **Owner:** team-reporting
- **Health:** 65 runs in 90 days; 63 succeeded, 2 failed
- **Migration target:** Could remain as GHA workflow on self-hosted runner if network access is maintained, or migrate to scheduled ETL platform.

### 4.5 Attestation Backfill — `attestation-backfill-weekly` (ID 114)
- **Schedule:** Sunday at 03:00 UTC
- **Pool:** `linux-build-workers` (self-hosted, 16GB RAM, 4 cores)
- **Timeout:** 180 minutes (inner step: 120 min)
- **What it does:** Scans compliance-store for attestation gaps, regenerates missing records
- **Dependencies:** requests, pandas
- **Network:** Requires internal network + compliance-store access
- **Owner:** shared-ci-platform
- **Health:** 13 runs in 90 days; 13 succeeded, 0 failed
- **Migration target:** Can migrate to GHA scheduled workflow on self-hosted runner, or to a lightweight scheduled job.

### 4.6 Regulatory Reporting — `regulatory-reporting-ci` (ID 107)
- **Schedule:** Weekdays at 06:00 UTC + CI trigger
- **Pool:** Azure Pipelines (hosted)
- **Timeout:** 90 minutes on report generation step
- **What it does:** Builds compliance package, generates regulatory reports, uploads attestation records to `attestation-database`. Does NOT produce a deployable artifact.
- **Owner:** team-reporting
- **Health:** 65 runs in 90 days; 61 succeeded, 4 failed. 82.4 min avg.
- **Migration note:** Classified as "build" in ADO but is actually a compliance workflow. 365-day retention for audit. Can migrate to GHA but the workflow steps need careful audit.

### 4.7 Bulk Trade Reprocessing — `bulk-reprocess-trades` (ID 115)
- **Schedule:** Manual trigger only
- **Pool:** Azure Pipelines (hosted)
- **Timeout:** 480 minutes (inner step: 420 min)
- **What it does:** Reprocesses trade data for a given date range and trade type
- **Owner:** **Unknown**
- **Health:** 3 runs in 90 days; 3 succeeded. Last run Feb 2026.
- **Migration target:** Low priority. Manual workflow; could be a GHA `workflow_dispatch` with parameters, or a standalone script.

---

## 5. Ownership Summary

### Confirmed Owners (High/Medium Confidence)

| Team | Pipelines Owned | Templates Owned |
|---|---|---|
| **team-quant** | portfolio-api-ci (102), portfolio-api-canary (103), risk-batch-ci (104), risk-batch-legacy (105), market-sim-ci (108), var-scenario-sweep-nightly (112) | `alt-templates/data-science/*`, `staging/preprod` branch modifications |
| **team-frontend** | frontend-workbench-ci (106) | `alt-templates/frontend/*`, `team/frontend-custom` branch |
| **team-reporting** | regulatory-reporting-ci (107), daily-positions-export (113) | `alt-templates/team-overrides/*`, `team/reporting-hotfix` branch |
| **platform-team** | ops-control-plane-ci (109) | — |
| **shared-ci-platform** | attestation-backfill-weekly (114) | All central templates (`templates/*`), `main` branch |

### Unknown / Unconfirmed Owners

| Pipeline | Suspected Owner | Last Modified By | Notes |
|---|---|---|---|
| pricing-engine-ci (101) | none | contractor-account@contoso.com | Original team disbanded |
| notebook-executor-nightly (110) | unknown | unknown-service-account@contoso.com | No owner identified; runs nightly |
| scenario-runner-weekly (111) | team-quant? | unknown-service-account@contoso.com | Appears to be quant project |
| bulk-reprocess-trades (115) | unknown | unknown-service-account@contoso.com | Unclear ownership |
| onetime-data-migration (116) | unknown | unknown-service-account@contoso.com | Should be deleted |

---

## 6. Template Duplication Findings

### Duplicate Set 1: Python Build Templates (4 copies)
Nearly identical Python build templates exist across 4 locations:

| Template | Location | Default Python | Key Differences |
|---|---|---|---|
| `build-python.yml` (central) | `templates/build/` | 3.11 | Canonical. Linting, pytest, coverage, Artifactory publish. |
| `build-python.yml` (data-science) | `alt-templates/data-science/` | 3.10 | Adds notebook execution, `requirements-ds.txt`. **Not referenced by any pipeline.** |
| `ds-model-build.yml` | `alt-templates/data-science/` | 3.10 | Nearly identical to `build-python.yml` (data-science) minus notebook execution. **Not referenced.** |
| `notebook-package-build.yml` | `alt-templates/data-science/` | 3.10 | Nearly identical to `ds-model-build.yml` with `jupyter` added. **Not referenced.** |

**Impact:** 3 unreferenced duplicates can be deleted.

### Duplicate Set 2: Python Build with Retry Logic (3 copies)
Retry logic was independently implemented in 3 places:

| Location | Retry Mechanism |
|---|---|
| `staging/preprod` branch: `templates/build/build-python.yml` | `pytest-rerunfailures` + shell retry loop with `testRetryCount` param |
| `services/risk-batch/pipeline-fragments/build-python-local.yml` | Shell retry loop (not currently referenced) |
| `alt-templates/data-science/python-batch.yml` | Shell retry loop with `retryCount` param (not referenced by any pipeline) |

**Impact:** Retry logic should be standardized in the canonical `build-python.yml` on `main`.

### Duplicate Set 3: .NET Build Variants (2 copies)
The .NET build template is frozen at different versions across branches:

| Branch | .NET Version | Last Reviewed |
|---|---|---|
| `main` | 8.0.x | 2024-08 |
| `master` | 6.0.x | 2023-09 |
| `legacy/master-support` | 6.0.x | 2022-12 (FROZEN) |

**Impact:** `master` and `legacy/master-support` have stale .NET 6.0.x templates. After migration, only the `main` version (8.0.x) should be carried forward.

### Duplicate Set 4: Frontend Build vs Central Node Build (2 copies)
| Template | SSR Support | Storybook | Lighthouse CI | Node Default |
|---|---|---|---|---|
| `templates/build/build-node.yml` (main) | No | No | No | 20.x |
| `alt-templates/frontend/frontend-build.yml` | Yes | No | No | 18.x |
| `templates/build/build-node.yml` (team/frontend-custom) | Yes | Yes | No | 18.x |
| `alt-templates/frontend/frontend-build.yml` (team/frontend-custom) | Yes | No | Yes (added) | 18.x |

**Impact:** SSR support was added to both the alt-template and the modified central template on `team/frontend-custom`. Consolidate into a single GHA reusable workflow.

---

## 7. Risk Flags for Migration

### 🔴 High Risk

| Risk | Pipelines Affected | Details |
|---|---|---|
| **Self-hosted pool: `high-memory-pool`** | 111, 112 | 128GB RAM, 32 cores. Non-build compute workloads (Monte Carlo, VaR). Cannot migrate to GHA hosted runners. Requires dedicated compute infrastructure. |
| **Self-hosted pool: `linux-build-workers`** | 110, 113, 114 | Internal network access (compliance-store, positions-db, data-warehouse, SMTP). Cannot migrate to GHA hosted runners without network peering. |
| **Long timeouts (>60 min)** | 107 (90 min), 110 (180 min), 111 (360 min), 112 (240 min), 113 (120 min), 114 (180 min), 115 (480 min) | GHA hosted runners have a 6-hour max. Self-hosted has no limit. Bulk-reprocess (115) runs up to 8 hours. |
| **No owner for active pipelines** | 101, 110, 111, 115 | 4 active pipelines with unknown ownership. Migration will stall without owners to validate GHA equivalents. |

### 🟡 Medium Risk

| Risk | Pipelines Affected | Details |
|---|---|---|
| **Branch-pinned template references** | 102 (master), 104 (staging/preprod), 105 (legacy/master-support), 106 (team/frontend-custom), 107 (team/reporting-hotfix) | 5 pipelines reference non-main branches. Templates on these branches have diverged. Need reconciliation before migration. |
| **ADO-specific features: `##vso` commands** | 110 | `##vso[task.logissue]`, `##vso[task.prependpath]` — these must be replaced with GHA `::warning::`, `echo "PATH=..." >> $GITHUB_PATH`. |
| **ADO-specific features: `pipeline.startTime`** | 112, 113 | `$[format('{0:yyyy-MM-dd}', pipeline.startTime)]` — no direct GHA equivalent. Use `$(date)` shell command or `${{ github.event.created_at }}`. |
| **ADO-specific features: deployment jobs** | 101, 102, 104, 106, 107 | `deployment:` job type with `strategy: runOnce` — replace with GHA `environment:` and deployment protection rules. |
| **ADO-specific features: `PublishBuildArtifacts@1`** | All 18 | Replace with `actions/upload-artifact@v4`. |
| **ADO-specific features: `resources.repositories`** | 101–107 | Template repos via `type: git` + branch ref — replace with GHA reusable workflows (`uses: org/repo/.github/workflows/x.yml@ref`). |
| **Regulatory compliance retention** | 107, 114 | 365-day artifact retention required for audit. GHA default is 90 days; must configure custom retention or external archive. |

### 🟢 Low Risk

| Risk | Pipelines Affected | Details |
|---|---|---|
| **Hosted pool mappings** | 101–109, 115–118 | `vmImage: ubuntu-latest` → `runs-on: ubuntu-latest`. Direct mapping. |
| **Inline custom pipelines** | 108, 109 | Straightforward translation of inline steps to GHA jobs. |
| **Schedule syntax** | 107, 110–114 | ADO cron → GHA `schedule: cron:`. Identical syntax. |

---

## 8. Branch Analysis with Actual Diffs

### 8.1 `master` vs `main`

**Summary:** Older .NET and Python template versions (pre-rename default branch).

```diff
diff --git a/templates/build/build-dotnet.yml b/templates/build/build-dotnet.yml
index d035442..44aaeb9 100644
--- a/templates/build/build-dotnet.yml
+++ b/templates/build/build-dotnet.yml
@@ -1,6 +1,6 @@
 # Central .NET build template
 # Maintained by: shared-ci-platform team
-# Last reviewed: 2024-08
+# Last reviewed: 2023-09
 
 parameters:
   - name: solution
@@ -11,7 +11,7 @@ parameters:
     default: 'Release'
   - name: dotnetVersion
     type: string
-    default: '8.0.x'
+    default: '6.0.x'
   - name: publishArtifacts
     type: boolean
     default: true
diff --git a/templates/build/build-python.yml b/templates/build/build-python.yml
index beae707..c6bb061 100644
--- a/templates/build/build-python.yml
+++ b/templates/build/build-python.yml
@@ -1,11 +1,11 @@
 # Central Python build template
 # Maintained by: shared-ci-platform team
-# Last reviewed: 2024-06
+# Last reviewed: 2023-11
 
 parameters:
   - name: pythonVersion
     type: string
-    default: '3.11'
+    default: '3.10'
   - name: requirementsFile
     type: string
     default: 'requirements.txt'
@@ -23,10 +23,10 @@ parameters:
     default: true
   - name: artifactName
     type: string
-    default: 'python-dist'
+    default: 'python-package'
   - name: enableLinting
     type: boolean
-    default: true
+    default: false
 
 steps:
   - task: UsePythonVersion@0
```

**Impact:** portfolio-api-ci (102) consumes `master`. Gets .NET 6.0.x defaults and Python 3.10 with linting disabled.

---

### 8.2 `staging/preprod` vs `main`

**Summary:** Adds test retry logic to the Python build template + preprod validation stamp.

```diff
diff --git a/templates/build/build-python.yml b/templates/build/build-python.yml
index beae707..6e5b560 100644
--- a/templates/build/build-python.yml
+++ b/templates/build/build-python.yml
@@ -1,6 +1,7 @@
 # Central Python build template
 # Maintained by: shared-ci-platform team
 # Last reviewed: 2024-06
+# Modified on staging/preprod: added retry logic for flaky tests (team-quant request)
 
 parameters:
   - name: pythonVersion
@@ -27,6 +28,9 @@ parameters:
   - name: enableLinting
     type: boolean
     default: true
+  - name: testRetryCount
+    type: number
+    default: 3
 
 steps:
   - task: UsePythonVersion@0
@@ -48,12 +52,23 @@ steps:
 
   - ${{ if eq(parameters.runTests, true) }}:
     - script: |
-        pip install pytest pytest-cov pytest-junitxml
-        pytest tests/ \
+        pip install pytest pytest-cov pytest-junitxml pytest-rerunfailures
+        RETRY=0
+        MAX_RETRY=${{ parameters.testRetryCount }}
+        until pytest tests/ \
           --junitxml=$(Build.ArtifactStagingDirectory)/test-results.xml \
           --cov=src/ \
-          --cov-report=xml:$(Build.ArtifactStagingDirectory)/coverage.xml
-      displayName: 'Run tests with coverage'
+          --cov-report=xml:$(Build.ArtifactStagingDirectory)/coverage.xml \
+          --reruns 2 --reruns-delay 5; do
+          RETRY=$((RETRY + 1))
+          if [ $RETRY -ge $MAX_RETRY ]; then
+            echo "Tests failed after $MAX_RETRY retries"
+            exit 1
+          fi
+          echo "Test retry $RETRY of $MAX_RETRY..."
+          sleep 10
+        done
+      displayName: 'Run tests with coverage (retry-enabled)'
 
     - task: PublishTestResults@2
       displayName: 'Publish test results'
@@ -80,3 +95,8 @@ steps:
           --registry artifact-registry \
           --build-id $(Build.BuildId)
       displayName: 'Register artifact in artifact-registry'
+
+    - script: |
+        echo "Preprod artifact validation stamp"
+        echo "$(Build.BuildId)" > $(Build.ArtifactStagingDirectory)/preprod-stamp.txt
+      displayName: 'Stamp preprod validation marker'
```

**Impact:** risk-batch-ci (104) consumes this branch. Gets `testRetryCount` parameter and `pytest-rerunfailures`.

---

### 8.3 `staging/release-hardening` vs `main`

**Summary:** Adds pre-deploy validation, mandatory approvals, and post-deploy health checks to the release template.

```diff
diff --git a/templates/release/release-standard.yml b/templates/release/release-standard.yml
index 7f5c07d..8fb5935 100644
--- a/templates/release/release-standard.yml
+++ b/templates/release/release-standard.yml
@@ -1,5 +1,6 @@
 # Central release pipeline template
 # Maintained by: shared-ci-platform team
+# Modified on staging/release-hardening: added pre-deploy validation and mandatory approvals
 
 parameters:
   - name: environment
@@ -19,10 +20,16 @@ parameters:
       - canary
   - name: requireApproval
     type: boolean
-    default: false
+    default: true
   - name: notifyReleaseOrchestrator
     type: boolean
     default: true
+  - name: runPreDeployValidation
+    type: boolean
+    default: true
+  - name: healthCheckRetries
+    type: number
+    default: 5
 
 stages:
   - stage: Deploy_${{ parameters.environment }}
@@ -42,11 +49,33 @@ stages:
                 - download: current
                   artifact: ${{ parameters.artifactName }}
 
+                - ${{ if eq(parameters.runPreDeployValidation, true) }}:
+                  - script: |
+                      echo "Running pre-deploy validation..."
+                      python $(Build.SourcesDirectory)/build-tools/scripts/compare_build_outputs.py \
+                        --artifact ${{ parameters.artifactName }} \
+                        --baseline $(Build.SourcesDirectory)/validation/baselines/
+                    displayName: 'Pre-deploy artifact validation'
+
                 - script: |
                     echo "Deploying ${{ parameters.artifactName }} to ${{ parameters.environment }}"
                     echo "Strategy: ${{ parameters.deployStrategy }}"
                   displayName: 'Execute deployment'
 
+                - script: |
+                    RETRY=0
+                    MAX_RETRY=${{ parameters.healthCheckRetries }}
+                    until curl -sf http://localhost:8080/health; do
+                      RETRY=$((RETRY + 1))
+                      if [ $RETRY -ge $MAX_RETRY ]; then
+                        echo "Health check failed after $MAX_RETRY attempts"
+                        exit 1
+                      fi
+                      echo "Health check retry $RETRY/$MAX_RETRY..."
+                      sleep 15
+                    done
+                  displayName: 'Post-deploy health check (hardened)'
+
                 - ${{ if eq(parameters.notifyReleaseOrchestrator, true) }}:
                   - script: |
                       python $(Build.SourcesDirectory)/build-tools/scripts/notify_release_orchestrator.py \
```

**Impact:** portfolio-api-canary (103) can select this branch via parameter. Adds mandatory approvals (`requireApproval` defaults to `true`), pre-deploy baseline validation, and retrying health checks.

---

### 8.4 `team/frontend-custom` vs `main`

**Summary:** Adds SSR/Storybook support to node template + Lighthouse CI to frontend build + artifact name includes build ID.

```diff
diff --git a/alt-templates/frontend/frontend-build.yml b/alt-templates/frontend/frontend-build.yml
index 5adba85..c2243bf 100644
--- a/alt-templates/frontend/frontend-build.yml
+++ b/alt-templates/frontend/frontend-build.yml
@@ -51,8 +51,12 @@ steps:
       archiveType: 'zip'
       archiveFile: '$(Build.ArtifactStagingDirectory)/${{ parameters.artifactName }}.zip'
 
+  - script: |
+      npx lhci autorun --collect.staticDistDir=build/ || true
+    displayName: 'Run Lighthouse CI audit'
+
   - task: PublishBuildArtifacts@1
     displayName: 'Upload frontend bundle'
     inputs:
       pathToPublish: '$(Build.ArtifactStagingDirectory)'
-      artifactName: ${{ parameters.artifactName }}
+      artifactName: '${{ parameters.artifactName }}-$(Build.BuildId)'
diff --git a/templates/build/build-node.yml b/templates/build/build-node.yml
index 5f7c374..0fd769f 100644
--- a/templates/build/build-node.yml
+++ b/templates/build/build-node.yml
@@ -1,11 +1,12 @@
 # Central Node.js build template
 # Maintained by: shared-ci-platform team
 # Last reviewed: 2024-07
+# Modified by team-frontend: SSR support, Storybook build, custom webpack
 
 parameters:
   - name: nodeVersion
     type: string
-    default: '20.x'
+    default: '18.x'
   - name: packageManager
     type: string
     default: 'npm'
@@ -24,6 +25,12 @@ parameters:
   - name: artifactName
     type: string
     default: 'node-dist'
+  - name: enableSSR
+    type: boolean
+    default: true
+  - name: buildStorybook
+    type: boolean
+    default: false
 
 steps:
   - task: NodeTool@0
@@ -42,6 +49,14 @@ steps:
   - script: ${{ parameters.packageManager }} run ${{ parameters.buildScript }}
     displayName: 'Build project'
 
+  - ${{ if eq(parameters.enableSSR, true) }}:
+    - script: ${{ parameters.packageManager }} run build:ssr
+      displayName: 'Build SSR bundle'
+
+  - ${{ if eq(parameters.buildStorybook, true) }}:
+    - script: ${{ parameters.packageManager }} run build-storybook
+      displayName: 'Build Storybook'
+
   - ${{ if eq(parameters.runTests, true) }}:
     - script: ${{ parameters.packageManager }} test -- --ci --reporters=jest-junit
       displayName: 'Run tests'
```

**Impact:** frontend-workbench-ci (106) consumes this branch. Gets Lighthouse CI audit, build ID in artifact name, SSR/Storybook support in node template.

---

### 8.5 `team/quant-experiments` vs `main`

**Summary:** Adds conda support, GPU pool option, and extended timeouts to the Python build template.

```diff
diff --git a/templates/build/build-python.yml b/templates/build/build-python.yml
index beae707..d986ba1 100644
--- a/templates/build/build-python.yml
+++ b/templates/build/build-python.yml
@@ -1,6 +1,7 @@
 # Central Python build template
 # Maintained by: shared-ci-platform team
 # Last reviewed: 2024-06
+# Modified by team-quant: added conda support, GPU pool option, extended timeouts
 
 parameters:
   - name: pythonVersion
@@ -27,6 +28,18 @@ parameters:
   - name: enableLinting
     type: boolean
     default: true
+  - name: useConda
+    type: boolean
+    default: false
+  - name: condaEnvironmentFile
+    type: string
+    default: 'environment.yml'
+  - name: useGpuPool
+    type: boolean
+    default: false
+  - name: timeoutMinutes
+    type: number
+    default: 60
 
 steps:
   - task: UsePythonVersion@0
@@ -34,10 +47,17 @@ steps:
     inputs:
       versionSpec: ${{ parameters.pythonVersion }}
 
-  - script: |
-      python -m pip install --upgrade pip setuptools wheel
-      pip install -r ${{ parameters.requirementsFile }}
-    displayName: 'Install dependencies'
+  - ${{ if eq(parameters.useConda, true) }}:
+    - script: |
+        conda env create -f ${{ parameters.condaEnvironmentFile }} || conda env update -f ${{ parameters.condaEnvironmentFile }}
+        conda activate $(basename ${{ parameters.condaEnvironmentFile }} .yml)
+      displayName: 'Setup conda environment'
+
+  - ${{ if eq(parameters.useConda, false) }}:
+    - script: |
+        python -m pip install --upgrade pip setuptools wheel
+        pip install -r ${{ parameters.requirementsFile }}
+      displayName: 'Install dependencies'
 
   - ${{ if eq(parameters.enableLinting, true) }}:
     - script: |
```

**Impact:** No confirmed active consumer. Experimental branch with useful features (conda, GPU, timeouts) that should be evaluated for merging into `main`.

---

### 8.6 `team/reporting-hotfix` vs `main`

**Summary:** Adds audit trail logging and pre-build compliance validation to the team-overrides template.

```diff
diff --git a/alt-templates/team-overrides/team-build-custom.yml b/alt-templates/team-overrides/team-build-custom.yml
index 942902e..fd826cb 100644
--- a/alt-templates/team-overrides/team-build-custom.yml
+++ b/alt-templates/team-overrides/team-build-custom.yml
@@ -2,6 +2,7 @@
 # Created by: team-reporting
 # Reason: Needed extra compliance metadata generation that central templates don't provide
 # This template wraps the central build and adds compliance steps
+# HOTFIX: Added audit trail logging and pre-build compliance validation (2024-07)
 
 parameters:
   - name: language
@@ -27,7 +28,18 @@ steps:
   - script: |
       echo "Build initiated with compliance level: ${{ parameters.complianceLevel }}"
       echo "Language: ${{ parameters.language }}"
-    displayName: 'Log compliance context'
+      echo "Audit trail: $(Build.BuildId) | $(Build.RequestedFor) | $(Build.SourceBranch)"
+      echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
+    displayName: 'Log compliance context with audit trail'
+
+  - script: |
+      echo "Pre-build compliance validation..."
+      python $(Build.SourcesDirectory)/build-tools/compliance/generate_metadata.py \
+        --artifact pre-build-check \
+        --compliance-level ${{ parameters.complianceLevel }} \
+        --build-id $(Build.BuildId) \
+        --store compliance-store
+    displayName: 'Pre-build compliance validation'
 
   - ${{ if eq(parameters.language, 'python') }}:
     - task: UsePythonVersion@0
@@ -58,6 +70,12 @@ steps:
           --store compliance-store
       displayName: 'Generate compliance metadata'
 
+    - script: |
+        echo "Generating audit trail record..."
+        echo '{"build_id": "$(Build.BuildId)", "compliance_level": "${{ parameters.complianceLevel }}", "status": "complete"}' \
+          > $(Build.ArtifactStagingDirectory)/audit-trail.json
+      displayName: 'Write audit trail record'
+
   - task: PublishBuildArtifacts@1
     displayName: 'Publish artifacts'
     inputs:
```

**Impact:** regulatory-reporting-ci (107) consumes this branch. Gets audit trail logging, pre-build compliance validation, and audit-trail.json artifact.

---

### 8.7 `legacy/master-support` vs `main`

**Summary:** Frozen branch with old .NET 6.0.x and Python 3.8 defaults. FROZEN banner added.

```diff
diff --git a/templates/build/build-dotnet.yml b/templates/build/build-dotnet.yml
index d035442..a2f4e4b 100644
--- a/templates/build/build-dotnet.yml
+++ b/templates/build/build-dotnet.yml
@@ -1,6 +1,7 @@
 # Central .NET build template
 # Maintained by: shared-ci-platform team
-# Last reviewed: 2024-08
+# Last reviewed: 2022-12
+# FROZEN: This branch is for legacy compatibility only. Do not modify.
 
 parameters:
   - name: solution
@@ -11,7 +12,7 @@ parameters:
     default: 'Release'
   - name: dotnetVersion
     type: string
-    default: '8.0.x'
+    default: '6.0.x'
   - name: publishArtifacts
     type: boolean
     default: true
diff --git a/templates/build/build-python.yml b/templates/build/build-python.yml
index beae707..74d49dc 100644
--- a/templates/build/build-python.yml
+++ b/templates/build/build-python.yml
@@ -1,11 +1,12 @@
 # Central Python build template
 # Maintained by: shared-ci-platform team
-# Last reviewed: 2024-06
+# Last reviewed: 2022-12
+# FROZEN: This branch is for legacy compatibility only. Do not modify.
 
 parameters:
   - name: pythonVersion
     type: string
-    default: '3.11'
+    default: '3.8'
   - name: requirementsFile
     type: string
     default: 'requirements.txt'
@@ -23,10 +24,10 @@ parameters:
     default: true
   - name: artifactName
     type: string
-    default: 'python-dist'
+    default: 'python-legacy-dist'
   - name: enableLinting
     type: boolean
-    default: true
+    default: false
 
 steps:
   - task: UsePythonVersion@0
```

**Impact:** risk-batch-legacy (105) and old-pricing-pipeline (117, disabled) reference this branch. Python 3.8 (EOL), .NET 6.0.x, linting disabled, FROZEN.

---

## 9. Variable Group & Secret Mapping

### Mapping: 9 ADO Variable Groups → GitHub Actions Equivalents

| # | Variable Group | ADO ID | Consuming Pipelines | Variables (Secret?) | GHA Equivalent | Scope |
|---|---|---|---|---|---|---|
| 1 | **shared-ci-secrets** | 201 | 101, 102, 103, 104, 105, 106, 107, 109 | `NUGET_FEED_URL`, `NUGET_API_KEY` 🔒, `PIP_INDEX_URL`, `NPM_REGISTRY`, `NPM_TOKEN` 🔒 | **Organization secrets** | Org-level: shared across 8 pipelines |
| 2 | **artifact-registry-credentials** | 205 | 101, 102, 104 | `ARTIFACT_REGISTRY_URL`, `ARTIFACT_REGISTRY_TOKEN` 🔒 | **Organization secrets** | Org-level: shared across 3 pipelines |
| 3 | **compliance-store-credentials** | 206 | 107, 114 | `COMPLIANCE_STORE_URL`, `COMPLIANCE_STORE_TOKEN` 🔒, `COMPLIANCE_STORE_CERT_THUMBPRINT` 🔒 | **Repository secrets** + **Environment secrets** (prod) | Repo-level for URL; env-level for tokens (compliance-sensitive) |
| 4 | **internal-network-credentials** | 207 | 110, 111, 112, 113, 115 | `INTERNAL_SVC_ACCOUNT`, `INTERNAL_SVC_PASSWORD` 🔒, `INTERNAL_CA_CERT_PATH` | **Organization secrets** | Org-level: used by 5 pipelines for internal network access |
| 5 | **risk-batch-config** | 208 | 104 | `RISK_DB_CONNECTION_STRING` 🔒, `RISK_MODEL_VERSION`, `RISK_BATCH_MAX_RETRIES` | **Repository secrets** (conn string) + **Repository variables** (non-secrets) | Repo-level: single pipeline |
| 6 | **regulatory-reporting-config** | 209 | 107 | `REPORTING_DB_CONNECTION_STRING` 🔒, `REPORTING_SMTP_SERVER`, `REPORTING_DISTRIBUTION_LIST` | **Environment secrets** (prod) + **Repository variables** | Env-level for DB conn; repo variables for non-secrets |
| 7 | **frontend-cdn-config** | 210 | 106 | `CDN_ENDPOINT`, `CDN_STORAGE_ACCOUNT`, `CDN_STORAGE_KEY` 🔒, `CDN_PURGE_API_KEY` 🔒 | **Environment secrets** (per env: dev-frontend, staging-frontend) | Env-level: different CDN configs per environment |
| 8 | **ops-infra-credentials** | 211 | 109 | `K8S_CLUSTER_URL`, `K8S_SERVICE_ACCOUNT_TOKEN` 🔒, `K8S_NAMESPACE` | **Repository secrets** (token) + **Repository variables** (URL, namespace). Consider **OIDC** for K8s auth. | Repo-level: single pipeline |
| 9 | **data-warehouse-credentials** | 212 | 112 | `DW_CONNECTION_STRING` 🔒, `DW_SCHEMA` | **Repository secrets** (conn string) + **Repository variables** (schema) | Repo-level: single pipeline |
| — | **positions-db-credentials** | 213 | 113, 116 | `POSITIONS_DB_CONNECTION_STRING` 🔒, `POSITIONS_DB_READONLY_STRING` 🔒 | **Repository secrets** | Repo-level: 2 pipelines (one is dead) |

### Recommended GHA Secret Architecture

```
Organization Secrets (shared across repos):
├── NUGET_FEED_URL
├── NUGET_API_KEY
├── PIP_INDEX_URL
├── NPM_REGISTRY
├── NPM_TOKEN
├── ARTIFACT_REGISTRY_URL
├── ARTIFACT_REGISTRY_TOKEN
├── INTERNAL_SVC_ACCOUNT
├── INTERNAL_SVC_PASSWORD
└── INTERNAL_CA_CERT_PATH

Repository Secrets (repo-specific):
├── RISK_DB_CONNECTION_STRING
├── COMPLIANCE_STORE_TOKEN
├── COMPLIANCE_STORE_CERT_THUMBPRINT
├── REPORTING_DB_CONNECTION_STRING
├── K8S_SERVICE_ACCOUNT_TOKEN
├── DW_CONNECTION_STRING
├── POSITIONS_DB_CONNECTION_STRING
└── POSITIONS_DB_READONLY_STRING

Environment Secrets (per-environment):
├── dev-frontend/
│   ├── CDN_STORAGE_KEY
│   └── CDN_PURGE_API_KEY
├── staging-frontend/
│   ├── CDN_STORAGE_KEY
│   └── CDN_PURGE_API_KEY
└── prod/
    ├── COMPLIANCE_STORE_TOKEN (restricted)
    └── REPORTING_DB_CONNECTION_STRING (restricted)

OIDC Candidates:
├── AzureSubscription-Dev → azure/login with OIDC federation
├── AzureSubscription-Staging → azure/login with OIDC federation
├── AzureSubscription-Prod → azure/login with OIDC federation
└── ops-infra-credentials → K8s OIDC token exchange
```

---

## 10. Service Connection Mapping

### 5 ADO Service Connections → GitHub Actions Equivalents

| # | Connection Name | ADO Type | Auth Scheme | Consuming Pipelines | GHA Equivalent | Notes |
|---|---|---|---|---|---|---|
| 1 | **AzureSubscription-Dev** | `azurerm` | ServicePrincipal (spnKey) | 101, 104, 106 | **`azure/login@v2` with OIDC** (federated credential) | Create OIDC federated credential for the `sp-dev-deploy-001` service principal. Use `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` as repo secrets. No client secret needed with OIDC. |
| 2 | **AzureSubscription-Staging** | `azurerm` | ServicePrincipal (spnKey) | 102, 106 | **`azure/login@v2` with OIDC** (federated credential) | Same pattern as Dev. Create separate federated credential for `sp-staging-deploy-001`. Restrict to `staging` environment in GHA. |
| 3 | **AzureSubscription-Prod** | `azurerm` | ServicePrincipal (spnKey) | 107 | **`azure/login@v2` with OIDC** (federated credential) | Same pattern. Create federated credential for `sp-prod-deploy-001`. Restrict to `prod` environment with required reviewers. |
| 4 | **ContainerRegistry-ACR** | `dockerregistry` | ServicePrincipal | 108, 109 | **`azure/docker-login@v2`** or **`docker/login-action@v3`** with OIDC | Use `azure/login@v2` first for OIDC, then `az acr login`. Registry: `contosofinancial.azurecr.io`. |
| 5 | **GitHub-SourceMirror** | `github` | PersonalAccessToken | _(none active)_ | **Not needed** | Was used for syncing upstream references. No active pipeline consumer. Skip in migration. |

### Migration Steps for Azure OIDC

For each `azurerm` service connection:

1. In Azure AD, add a federated credential to the existing service principal:
   - Issuer: `https://token.actions.githubusercontent.com`
   - Subject: `repo:<org>/<repo>:environment:<env-name>` (e.g., `repo:contoso-financial/shared-ci-platform:environment:dev`)
   - Audience: `api://AzureADTokenExchange`
2. In GHA, configure environment secrets:
   - `AZURE_CLIENT_ID` = service principal app ID
   - `AZURE_TENANT_ID` = `t1e2n3a4-n5t6-i7d8-h9e0-re1234567890`
   - `AZURE_SUBSCRIPTION_ID` = target subscription
3. In the workflow:
   ```yaml
   - uses: azure/login@v2
     with:
       client-id: ${{ secrets.AZURE_CLIENT_ID }}
       tenant-id: ${{ secrets.AZURE_TENANT_ID }}
       subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
   ```

---

## 11. Environment & Approval Gate Mapping

### 6 ADO Environments → GitHub Environments with Protection Rules

| # | ADO Environment | Approval Checks | Business Hours Gate | Other Checks | Consuming Pipelines | GHA Environment Config |
|---|---|---|---|---|---|---|
| 1 | **dev** | None | None | None | 101, 104 | Create GH Environment `dev`. No protection rules. Auto-deploy. |
| 2 | **staging** | 1 approver from `shared-ci-platform-team` | None | None | 102 | Create GH Environment `staging`. Add **Required reviewers**: shared-ci-platform-team (min 1). |
| 3 | **preprod** | 2 approvers from `shared-ci-platform-team` + `release-managers` | EST 09:00–17:00, Mon–Fri | None | _(no active consumer)_ | Create GH Environment `preprod`. **Required reviewers**: 2 from {shared-ci-platform-team, release-managers}. **Deployment branches**: `main` only. **Wait timer**: use custom action or `actions/github-script` to enforce business hours — GHA has no native business hours gate. |
| 4 | **prod** | 2 approvers from `release-managers` + `service-owner` | EST 09:00–16:00, Mon–Thu | Exclusive lock (single deploy) | 107 | Create GH Environment `prod`. **Required reviewers**: 2 from {release-managers, service-owner}. **Deployment branches**: `main` only. Use **concurrency group** (`concurrency: group: prod-deploy, cancel-in-progress: false`) for exclusive lock. Business hours: custom action or scheduled check. |
| 5 | **dev-frontend** | None | None | None | 106 | Create GH Environment `dev-frontend`. No protection rules. Auto-deploy. |
| 6 | **staging-frontend** | 1 approver from `team-frontend` | None | None | 106 | Create GH Environment `staging-frontend`. **Required reviewers**: team-frontend (min 1). |

### Feature Gaps: ADO → GHA

| ADO Feature | GHA Equivalent | Gap? |
|---|---|---|
| Approval gates (min N approvers) | Required reviewers on environment | ✅ Direct mapping |
| Business hours check | No native equivalent | ⚠️ Needs custom action or external tool |
| Exclusive lock | `concurrency` group with `cancel-in-progress: false` | ✅ Close equivalent |
| Environment-scoped resources | Environment secrets + deployment branches | ✅ Direct mapping |

---

## 12. Agent Pool & Infrastructure Requirements

### 4 ADO Agent Pools → GHA Alternatives

| # | Pool Name | Type | Size | Specs | Consuming Pipelines | GHA Equivalent | Migration Complexity |
|---|---|---|---|---|---|---|---|
| 1 | **Azure Pipelines** | Hosted | Auto-scale | Standard hosted VMs | 101–109, 115–118 | **`runs-on: ubuntu-latest`** (or `windows-latest`, `macos-latest`) | 🟢 **Trivial.** Direct 1:1 mapping. |
| 2 | **linux-build-workers** | Self-hosted | 8 agents (6 online, 2 offline) | Ubuntu 22.04, 16GB RAM, 4 cores, 200GB disk. Python 3.10/3.11, Docker, Jupyter, conda. Internal network: compliance-store, positions-db, internal-smtp, data-warehouse. | 110, 113, 114 | **Self-hosted GHA runner** deployed in same network segment. Or migrate workloads to K8s CronJobs / Azure Container Instances. | 🔴 **High.** Requires network peering, internal CA cert, and internal service account setup on GHA self-hosted runner. |
| 3 | **high-memory-pool** | Self-hosted | 4 agents (all online) | Ubuntu 22.04, **128GB RAM**, **32 cores**, 1TB disk. Python 3.11, Docker, numpy, scipy, pyarrow. Internal network: compliance-store, positions-db, internal-smtp, data-warehouse, compute-cluster. | 111, 112 | **NOT GHA.** These workloads (Monte Carlo, VaR) should migrate to dedicated compute infrastructure: K8s Jobs, AWS Batch, Azure Container Instances, or a dedicated compute cluster. GHA runners (even self-hosted) are not designed for 4+ hour HPC workloads. | 🔴 **High.** These are not CI/CD workloads. Requires a compute platform migration, not a GHA migration. |
| 4 | **windows-build-workers** | Self-hosted (legacy) | 2 agents (1 online, 1 offline) | Windows Server 2019/2022, 32GB RAM, 8 cores, 500GB disk. .NET 6/8, NuGet, MSBuild. Internal SMTP only. | _(none active)_ | **Decommission.** No active pipeline references this pool. Verify with ADO pool override audit, then remove. | 🟢 **None.** Candidate for decommission. |

### Infrastructure Decision Matrix

| Workload Type | Current Pool | Recommended Target | Rationale |
|---|---|---|---|
| Standard CI/CD builds | Azure Pipelines | GHA hosted runners | Direct mapping, no infrastructure changes |
| Internal-network CI jobs | linux-build-workers | GHA self-hosted runner in internal network | Need same network access; deploy runner in same VPC/subnet |
| High-memory compute | high-memory-pool | K8s Jobs / AWS Batch / ACI | Not CI workloads; need 128GB RAM, 32 cores for HPC |
| Compliance/data jobs | linux-build-workers | GHA self-hosted runner OR K8s CronJob | Moderate compute; primarily needs network access |
| Nightly notebooks | linux-build-workers | K8s CronJob with Jupyter container | Better isolation and resource management |
| Ad-hoc trade reprocessing | Azure Pipelines | GHA `workflow_dispatch` | Low frequency; hosted runner sufficient |

---

## Summary Statistics

| Metric | Value |
|---|---|
| Total pipelines | 18 |
| Active pipelines (runs in 90 days) | 15 |
| Dead pipelines (skip in migration) | 3 |
| Non-build workloads | 5 (+ 2 hybrid/ad-hoc) |
| Unique template branches consumed | 6 (main, master, staging/preprod, team/frontend-custom, team/reporting-hotfix, legacy/master-support) |
| Unreferenced template files | 12 |
| Variable groups to migrate | 9 (containing 12 secrets) |
| Service connections to migrate | 4 (1 unused) |
| Environments to recreate | 6 |
| Self-hosted pools requiring infra work | 2 (linux-build-workers, high-memory-pool) |
| Pipelines with unknown owners | 5 |
| OIDC migration candidates | 3 Azure service connections |
