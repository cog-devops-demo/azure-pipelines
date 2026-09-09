# Migration Validation Strategy

## Overview

When migrating pipelines from ADO to GitHub Actions, each service must pass
validation checks that confirm the migrated workflow produces equivalent results.

## Validation Layers

### 1. Artifact Comparison

Compare build output artifacts:
- File count within 20% tolerance
- Expected file types present
- Artifact size within expected range

Tool: `validation/scripts/compare_artifacts.py`

### 2. Test Count Comparison

Compare test execution results:
- Total test count within 5% tolerance
- Pass rate meets minimum threshold
- No new test failures introduced

Tool: `validation/scripts/compare_test_counts.py`

### 3. Deployment Verification

After migration, verify:
- Deployment targets are identical
- Environment variables match
- Release-orchestrator receives notifications
- Compliance attestations are generated

### 4. Non-Build Workload Review

Pipelines classified as non-build workloads require separate review:
- Determine if they should migrate at all
- Consider alternative compute platforms
- Validate schedule equivalence if migrated

## Baseline Management

Baselines are stored in `validation/baselines/<service>/`.

Each service should have:
- `expected-artifacts.json` — artifact expectations
- `test-counts.json` — test execution expectations

## Running Validation

```bash
# Compare artifacts for a single service
python validation/scripts/compare_artifacts.py \
  --baseline validation/baselines/pricing-engine/expected-artifacts.json \
  --artifacts /path/to/gha/artifacts

# Compare test counts
python validation/scripts/compare_test_counts.py \
  --baseline validation/baselines/pricing-engine/test-counts.json \
  --actual /path/to/gha/test-results.json

# Generate summary report
python validation/scripts/summarize_build_results.py \
  --baselines validation/baselines/
```
