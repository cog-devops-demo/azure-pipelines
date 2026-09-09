#!/usr/bin/env python3
"""
Compare test execution counts between ADO and GitHub Actions runs.

Validates that the migrated pipeline runs the same number of tests
and achieves comparable pass rates.
"""

import argparse
import json
import sys


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def compare_test_counts(baseline_path: str, actual_path: str) -> dict:
    """Compare test counts from migrated pipeline against baseline."""
    baseline = load_json(baseline_path)
    actual = load_json(actual_path)

    results = {"passed": True, "checks": []}

    # Test count comparison
    expected_tests = baseline.get("expected_total_tests", 0)
    actual_tests = actual.get("total_tests", 0)
    count_ok = actual_tests >= expected_tests * 0.95  # Allow 5% tolerance
    results["checks"].append({
        "name": "test_count",
        "expected": expected_tests,
        "actual": actual_tests,
        "tolerance": "5%",
        "passed": count_ok,
    })
    if not count_ok:
        results["passed"] = False

    # Pass rate comparison
    min_pass_rate = baseline.get("minimum_pass_rate", 0.9)
    if actual_tests > 0:
        actual_passed = actual.get("total_passed", 0)
        actual_pass_rate = actual_passed / actual_tests
    else:
        actual_pass_rate = 0

    rate_ok = actual_pass_rate >= min_pass_rate
    results["checks"].append({
        "name": "pass_rate",
        "minimum": min_pass_rate,
        "actual": round(actual_pass_rate, 4),
        "passed": rate_ok,
    })
    if not rate_ok:
        results["passed"] = False

    return results


def main():
    parser = argparse.ArgumentParser(description="Compare test counts")
    parser.add_argument("--baseline", required=True, help="Baseline test counts JSON")
    parser.add_argument("--actual", required=True, help="Actual test results JSON")
    parser.add_argument("--output", help="Output path for comparison report")

    args = parser.parse_args()

    results = compare_test_counts(args.baseline, args.actual)
    print(json.dumps(results, indent=2))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
