#!/usr/bin/env python3
"""
Compare migrated pipeline artifacts against ADO baselines.

This script is intended for use during CI migration validation.
It compares artifacts produced by GitHub Actions workflows against
the baseline expectations from the original ADO pipelines.
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_baseline(baseline_path: str) -> dict:
    """Load a baseline expectation file."""
    with open(baseline_path) as f:
        return json.load(f)


def scan_artifacts(artifact_dir: str) -> dict:
    """Scan an artifact directory and collect metrics."""
    artifact_path = Path(artifact_dir)
    files = list(artifact_path.rglob("*"))
    file_list = [f for f in files if f.is_file()]

    total_size = sum(f.stat().st_size for f in file_list)
    extensions = set(f.suffix for f in file_list)

    return {
        "file_count": len(file_list),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "extensions": sorted(extensions),
        "files": [str(f.relative_to(artifact_path)) for f in file_list],
    }


def compare(baseline: dict, actual: dict) -> dict:
    """Compare actual artifacts against baseline expectations."""
    results = {"passed": True, "checks": []}

    # Check file count
    expected_count = baseline.get("expected_file_count", 0)
    actual_count = actual["file_count"]
    count_ok = actual_count >= expected_count * 0.8
    results["checks"].append({
        "name": "file_count",
        "expected": expected_count,
        "actual": actual_count,
        "passed": count_ok,
    })
    if not count_ok:
        results["passed"] = False

    # Check file types
    expected_types = set(baseline.get("expected_file_types", []))
    actual_types = set(actual["extensions"])
    types_ok = expected_types.issubset(actual_types)
    results["checks"].append({
        "name": "file_types",
        "expected": sorted(expected_types),
        "actual": sorted(actual_types),
        "passed": types_ok,
    })
    if not types_ok:
        results["passed"] = False

    # Check artifact size
    min_size = baseline.get("min_artifact_size_mb", 0)
    max_size = baseline.get("max_artifact_size_mb", float("inf"))
    size_ok = min_size <= actual["total_size_mb"] <= max_size
    results["checks"].append({
        "name": "artifact_size_mb",
        "expected_range": [min_size, max_size],
        "actual": actual["total_size_mb"],
        "passed": size_ok,
    })
    if not size_ok:
        results["passed"] = False

    return results


def main():
    parser = argparse.ArgumentParser(description="Compare artifacts against baselines")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON file")
    parser.add_argument("--artifacts", required=True, help="Path to artifact directory")
    parser.add_argument("--output", help="Output path for comparison report")

    args = parser.parse_args()

    baseline = load_baseline(args.baseline)
    actual = scan_artifacts(args.artifacts)
    results = compare(baseline, actual)

    print(json.dumps(results, indent=2))

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
