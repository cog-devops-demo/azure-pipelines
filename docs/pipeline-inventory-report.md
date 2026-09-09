# Azure DevOps Pipeline Inventory & Migration Disposition

Scope: all 18 ADO pipeline definitions (IDs 101–118) in this repository, plus the
template branches they consume.

Evidence sources:

- Pipeline YAML on `main`.
- ADO API snapshot `docs/samples/ado-api-responses.json` (generated `2026-03-17T23:00:00Z`)
  for ADO IDs, owners, queue status, pools, triggers, variable groups and run history.
- The seven long-lived template branches (`master`, `staging/preprod`,
  `staging/release-hardening`, `team/frontend-custom`, `team/quant-experiments`,
  `team/reporting-hotfix`, `legacy/master-support`), diffed against `main`.

Branch scope note: no template branch defines a pipeline that does not exist on `main`.
Diffs across `templates/`, `alt-templates/`, `build-tools/yaml/` and the service
pipelines are modifications only — no pipeline YAML is added or removed on any branch.
The branch dimension therefore changes *what a pipeline builds with*, not *how many
pipelines exist*. Per-branch template divergence is in the appendix.

## Disposition summary

| Disposition | Count | IDs |
| --- | --- | --- |
| Migrate to GitHub Actions | 9 | 101, 102, 103, 106, 107, 108, 109, 114, 115 |
| Leave on ADO / wrong platform (needs a compute platform, not CI) | 4 | 110, 111, 112, 113 |
| Dead — retire, do not migrate | 5 | 105, 116, 117, 118 (+ 105 flagged, see notes) |

Counts: 9 migrate, 4 wrong-platform, 4 dead (116, 117, 118 confirmed dead in ADO;
105 is a *proposed* retirement — it is still enabled and externally triggered, so it
is listed as dead-candidate and must be confirmed with team-quant before deletion).

## Master inventory

| ADO ID | Name | YAML path | Owner | Stack | Trigger | Templates consumed (branch) | Category | Risk flags | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 101 | pricing-engine-ci | `services/pricing-engine/azure-pipelines.yml` | **unknown** (last edit: contractor-account) | .NET (`UseDotNet@2`) | CI on `main`, `release/*`; path `services/pricing-engine/**` | `templates/build/build-dotnet.yml`, `templates/test/run-tests.yml`, `templates/release/release-standard.yml` — **`main`** | Central-template consumer | R1 no owner; R5 `deployment:`+`environment: dev`; R6 var groups `shared-ci-secrets`, `artifact-registry-credentials` | **Migrate to GHA** |
| 102 | portfolio-api-ci | `services/portfolio-api/azure-pipelines.yml` | team-quant | Java/Maven | CI on `main`, `master`; path `services/portfolio-api/**` | `templates/build/build-java.yml`, `templates/release/release-standard.yml` — **`master`** | Central-template consumer | R2 pinned to legacy `master` templates (older Maven goal + `artifact-registry` naming); R5 `environment: staging` w/ approval check; R6 var groups | **Migrate to GHA** |
| 103 | portfolio-api-canary | `services/portfolio-api/azure-pipelines-canary.yml` | team-quant | Java/Maven | Manual only (`trigger: none`), `templateBranch` parameter | `templates/build/build-java.yml` from **four** repos aliases: `main`, `master`, `staging/preprod`, `staging/release-hardening` | Central-template consumer (template test harness) | R3 multi-branch template fan-out — the clearest symptom of branch drift; R6 var group | **Migrate to GHA** (as a matrix workflow over reusable-workflow refs; becomes largely unnecessary once templates are unified) |
| 104 | risk-batch-ci | `services/risk-batch/azure-pipelines.yml` | team-quant | Python | CI on `main`; path `services/risk-batch/**` | `templates/build/build-python.yml`, `templates/test/run-tests.yml`, `templates/release/release-standard.yml` — **`staging/preprod`** | Central-template consumer | R2 depends on `staging/preprod` (unmaintained branch) for pip retry logic; R4 unused local fork `services/risk-batch/pipeline-fragments/build-python-local.yml`; R5 `environment: dev`; R6 3 var groups | **Migrate to GHA** |
| 105 | risk-batch-legacy | `services/risk-batch/azure-pipelines-legacy.yml` | team-quant (last edit: contractor-account) | Python (legacy) | `trigger: none`; triggered externally by downstream jobs | `templates/legacy/build-python-legacy.yml` — **`legacy/master-support`** (frozen) | Central-template consumer (legacy) | R2 frozen branch, stale Python 3.8 defaults, publishing disabled by default; R7 only 2 runs, last Jan 2026; R8 external trigger source is undocumented | **Dead candidate — retire** (confirm the downstream caller with team-quant first; do not port) |
| 106 | frontend-workbench-ci | `services/frontend-workbench/azure-pipelines.yml` | team-frontend | Node/TypeScript (Node 18.x on branch) | CI on `main`; path `services/frontend-workbench/**` | `alt-templates/frontend/frontend-build.yml`, `alt-templates/frontend/frontend-deploy.yml` (×2) — **`team/frontend-custom`** | Alt-template consumer | R2 team-owned template branch never merged to `main` (SSR/Storybook/Lighthouse steps live only there); R5 two `deployment:` jobs → `dev-frontend`, `staging-frontend` (approval check); R6 var groups | **Migrate to GHA** |
| 107 | regulatory-reporting-ci | `services/regulatory-reporting/azure-pipelines.yml` | team-reporting | Python | CI **and** schedule `0 6 * * 1-5` | `alt-templates/team-overrides/team-build-custom.yml` — **`team/reporting-hotfix`** + large inline compliance block | Hybrid (build shape, compliance workload) | R2 hotfix branch carries audit-trail logging not on `main`; R9 mis-shaped — a compliance workflow wearing a CI costume; R10 365-day retention (audit); R5 `prod` environment w/ 2-approver + business-hours + exclusive-lock checks; avg 82 min | **Migrate to GHA** (port the build half; the `prod` gate needs a GHA environment with required reviewers — exclusive-lock maps to concurrency groups) |
| 108 | market-sim-ci | `services/market-sim/azure-pipelines.yml` | team-quant | Rust (rustup/cargo) | CI on `main`; path filter | **None** — fully inline | Custom inline | R11 no template reuse; R12 `##vso[task.prependpath]`, `PublishBuildArtifacts@1`, `Build.SourceBranch` condition; R13 deploys to a compute cluster outside release-orchestrator | **Migrate to GHA** (self-contained; easiest port) |
| 109 | ops-control-plane-ci | `services/ops-control-plane/azure-pipelines.yml` | platform-team | Go (`GoTool@0`) | CI on `main`; path filter | **None** — fully inline (predates `templates/build/build-go.yml`) | Custom inline | R11 no template reuse; R6 var groups; R12 ACR service connection | **Migrate to GHA** |
| 110 | notebook-executor-nightly | `services/notebook-executor/azure-pipelines.yml` | **unknown** | Python / Jupyter | Schedule `0 2 * * *` (`always: true`) | **None** — inline | Non-build workload | R1 no owner; R14 self-hosted `linux-build-workers`, needs internal network; R15 3 h timeout, avg 165 min; R16 20 % of runs partially succeed (`##vso[task.logissue]` masks notebook failures); R17 CI used as free compute | **Leave on ADO / wrong platform** — this is scheduled batch compute, not CI. Target a job scheduler (K8s CronJob, Azure Container Instances, Airflow); do not port to GHA. |
| 111 | scenario-runner-weekly | `services/scenario-runner/azure-pipelines.yml` | **unknown** | Python (Monte Carlo) | Schedule `0 22 * * 5` + manual with parameters | **None** — inline | Non-build workload | R1 no owner; R14 `high-memory-pool` (128 GB / 32 cores) self-hosted; R15 6 h timeout, avg 228 min — exceeds the 6 h GHA hosted job limit; R17 CI used as compute | **Leave on ADO / wrong platform** — needs dedicated compute (AWS Batch / K8s / ACI). |
| 112 | var-scenario-sweep-nightly | `night-jobs/compute/var-scenario-sweep.yml` | team-quant | Python (VaR sweep, 50 000 scenarios) | Schedule `0 1 * * 1-5` | **None** — inline | Non-build workload | R14 `high-memory-pool`; R15 4 h timeout, avg 172 min; R12 `pipeline.startTime` expression has no GHA equivalent; R6 data-warehouse credentials | **Leave on ADO / wrong platform** — dedicated compute platform. |
| 113 | daily-positions-export | `night-jobs/business/daily-positions-export.yml` | team-reporting | Python (pyodbc, Excel) | Schedule `0 23 * * 1-5` | **None** — inline | Non-build workload | R14 `linux-build-workers`, direct `positions-db` + internal SMTP access; R15 avg 76 min; R18 emails business reports from a CI pipeline | **Leave on ADO / wrong platform** — this is a scheduled ETL + report distribution job; belongs in a data platform (Airflow/ADF), not GHA. |
| 114 | attestation-backfill-weekly | `night-jobs/compliance/attestation-backfill.yml` | shared-ci-platform | Python | Schedule `0 3 * * 0` | **None** — inline; calls `build-tools/compliance/generate_metadata.py` | Non-build workload (small, owned) | R14 `linux-build-workers` for `compliance-store` access; R10 365-day retention | **Migrate to GHA** — only non-build job with a clear owner and a modest footprint (avg 93 min); runs fine on a self-hosted GHA runner in the same network segment. |
| 115 | bulk-reprocess-trades | `adhoc/bulk-reprocess-trades.yml` | **unknown** | Python | Manual only (`trigger: none`) | **None** — inline | Ad-hoc (active) | R1 no owner; R15 8 h timeout, avg 325 min — **exceeds GHA's 6 h hosted job limit**; R6 internal-network credentials; R7 3 runs, last Feb 2026 | **Migrate to GHA** *with a caveat* — port as a `workflow_dispatch` workflow, but it must run on a self-hosted runner (or be re-homed as a batch job) because of the runtime limit. |
| 116 | onetime-data-migration | `adhoc/onetime-data-migration.yml` | **unknown** | Python | `trigger: none`; **paused in ADO** | **None** — inline | Ad-hoc stale | R19 paused; R7 one run, Aug 2024; R20 name says one-time and the one time has passed | **Dead — delete** |
| 117 | old-pricing-pipeline | `deprecated/old-pricing-pipeline.yml` | none | .NET 6 (inline) | `trigger: none`; **disabled in ADO** | Declares `templates` repo at **`legacy/master-support`** but builds inline | Deprecated | R19 disabled; R7 0 runs since Jun 2023; R21 superseded by 101 | **Dead — delete** |
| 118 | batch-runner-v1 | `deprecated/batch-runner-v1.yml` | none | Python 3.8 | `trigger: none`; **disabled in ADO** | **None** — inline | Deprecated | R19 disabled; R7 0 runs, last run failed Feb 2023; R21 superseded by 104 + night-jobs; R22 mixed build **and** compute in one definition (the anti-pattern this inventory exists to unwind) | **Dead — delete** |

## Categories

1. **Central-template consumer** (101, 102, 103, 104, 105) — consumes `templates/**`
   from the shared repo. The interesting variable is *which branch*: only 101 is on
   `main`. 102 is on `master`, 104 on `staging/preprod`, 105 on `legacy/master-support`,
   and 103 straddles four branches at once.
2. **Alt-template consumer** (106, 107) — consumes `alt-templates/**` from a team-owned
   branch that was never merged back.
3. **Custom inline** (108, 109) — no shared templates at all. Easiest to migrate,
   because there is no branch entanglement to resolve first.
4. **Non-build workload** (110, 111, 112, 113, 114) — scheduled compute, ETL, or
   compliance jobs that happen to be expressed as pipelines. Four of the five are the
   core "wrong platform" finding.
5. **Ad-hoc** (115, 116) — manually triggered utility pipelines.
6. **Deprecated** (117, 118) — disabled in ADO, retained for reference only.

## Why four pipelines should not go to GitHub Actions

110, 111, 112 and 113 are not CI. They are scheduled compute and data jobs that were
put on the build system because the build system had agents with the right network
access and enough RAM. Migrating them to GHA would reproduce that mistake on a new
platform, and in two cases (111 at ~228 min average with a 6 h ceiling, 112 at ~172 min)
it would not even fit inside GHA's hosted job limits. All four depend on the
self-hosted pools' internal network reachability (`positions-db`, `compliance-store`,
`data-warehouse`, internal SMTP), which no hosted runner has.

Recommendation: keep them on ADO until they are re-homed onto a compute/orchestration
platform (K8s CronJobs, AWS Batch, Azure Container Instances, or Airflow for 113),
and treat that re-homing as a separate workstream from the CI migration. 114 is the
exception — small, clearly owned, and portable to a self-hosted GHA runner.

## Ownership gaps

Five pipelines have no identified owner: 101, 110, 111, 115, 116. Four of those were
last modified by `contractor-account@contoso.com` or
`unknown-service-account@contoso.com`. 101 is the notable one — it is an active,
frequently run CI pipeline (47 runs) whose original team disbanded; `shared-ci-platform`
maintains it best-effort. Ownership must be assigned before migration, because
migrating a pipeline nobody owns just moves an orphan.

## Risk flag legend

| Flag | Meaning |
| --- | --- |
| R1 | No identified owning team |
| R2 | Depends on a non-`main` template branch (drift / unmaintained) |
| R3 | Consumes templates from multiple branches simultaneously |
| R4 | Unreferenced local template fork exists |
| R5 | Uses ADO `deployment:` jobs + `environment` with approval checks |
| R6 | Depends on ADO variable groups (external to YAML) |
| R7 | Little or no recent run history |
| R8 | Triggered by an undocumented external caller |
| R9 | Category mismatch — shaped like a build, is not one |
| R10 | Long (365-day) audit retention requirement |
| R11 | No template reuse — fully inline |
| R12 | ADO-specific constructs (`##vso`, `pipeline.startTime`, `PublishBuildArtifacts@1`) |
| R13 | Deploys outside the standard release path |
| R14 | Requires self-hosted agents / internal network access |
| R15 | Long runtime; may exceed GHA hosted job limits (6 h) |
| R16 | Silent partial failures |
| R17 | CI platform used as general-purpose compute |
| R18 | Distributes business output (email/reports) from CI |
| R19 | Paused or disabled in ADO |
| R20 | Superseded by its own purpose (one-time job, already run) |
| R21 | Superseded by another pipeline |
| R22 | Mixes build and compute in one definition |

## Appendix: template-branch divergence

Every branch below modifies shared templates only; none adds or removes a pipeline.

| Branch | Status | Consumed by | What it changes |
| --- | --- | --- | --- |
| `main` | Canonical | 101 | Baseline: .NET 8.0.x, Python 3.11, `Artifactory` naming |
| `master` | Legacy default | 102 (+103) | .NET default 6.0.x, Python 3.10, `mavenGoals`→`mavenGoal`, `Artifactory`→`artifact-registry`, `attestation-database`→`compliance-store` |
| `staging/preprod` | Active, unmaintained | 104 (+103) | pip retry logic, changed template parameters, preprod validation stamp |
| `staging/release-hardening` | Active | 103 only | Pre-deploy validation, mandatory approvals, health-check retries in release templates |
| `team/frontend-custom` | Active, team-owned | 106 | Node default 18.x, SSR + Storybook parameters/steps, Lighthouse in the frontend alt template |
| `team/quant-experiments` | Experimental | **none** | Optional conda, GPU-pool and timeout parameters on Python templates — no pipeline consumes it |
| `team/reporting-hotfix` | Active, team-owned | 107 | Compliance audit-trail logging, pre-build validation |
| `legacy/master-support` | Frozen | 105, 117 (declared) | .NET 6.0.x / Python 3.8 defaults, publishing disabled by default, frozen-compatibility banner |

Migration implication: unifying these branches onto reusable workflows is a
prerequisite for migrating 102, 103, 104, 106 and 107 — five of the nine
migration candidates. `team/quant-experiments` has no consumers and can be dropped.
