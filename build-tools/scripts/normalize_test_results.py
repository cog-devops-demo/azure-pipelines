#!/usr/bin/env python3
"""
Normalize test results from different frameworks into a common format.

Accepts JUnit XML, pytest JSON, or Jest JSON output and converts
to a unified schema for cross-service test reporting.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _strip_namespaces(root: ET.Element) -> None:
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]


def parse_junit_xml(filepath: str) -> dict:
    """Parse JUnit XML test results."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    _strip_namespaces(root)

    suites = root.findall(".//testsuite")
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for suite in suites:
        total_tests += int(suite.get("tests", 0))
        total_failures += int(suite.get("failures", 0))
        total_errors += int(suite.get("errors", 0))
        total_skipped += int(suite.get("skipped", 0))

    return {
        "total": total_tests,
        "passed": total_tests - total_failures - total_errors - total_skipped,
        "failed": total_failures + total_errors,
        "skipped": total_skipped,
    }


def parse_trx(filepath: str) -> dict:
    """Parse VSTest TRX results."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    _strip_namespaces(root)
    counters = root.find("./ResultSummary/Counters")
    if counters is None:
        raise ValueError("missing ResultSummary/Counters")

    total = int(counters.get("total", 0))
    passed = int(counters.get("passed", 0))
    failed = int(counters.get("failed", 0))
    errors = int(counters.get("error", 0))
    if counters.get("notExecuted") is not None:
        skipped = int(counters.get("notExecuted", 0))
    else:
        skipped = total - int(counters.get("executed", 0))

    return {
        "total": total,
        "passed": passed,
        "failed": failed + errors,
        "skipped": skipped,
    }


def normalize_results(input_dir: str, output_path: str):
    """Scan input directory and normalize all test result files."""
    results = []
    input_path = Path(input_dir)

    for f in input_path.rglob("*"):
        if f.suffix.lower() not in {".xml", ".trx"}:
            continue
        try:
            if f.suffix.lower() == ".trx":
                parsed = parse_trx(str(f))
                parsed["format"] = "trx"
            else:
                tree = ET.parse(f)
                root = tree.getroot()
                _strip_namespaces(root)
                if not list(root.iter("testsuite")):
                    print(f"WARNING: Skipping non-JUnit XML file {f}")
                    continue
                parsed = parse_junit_xml(str(f))
                parsed["format"] = "junit-xml"
            parsed["source"] = str(f.name)
            results.append(parsed)
        except Exception as e:
            print(f"WARNING: Could not parse {f}: {e}")

    summary = {
        "total_suites": len(results),
        "total_tests": sum(r["total"] for r in results),
        "total_passed": sum(r["passed"] for r in results),
        "total_failed": sum(r["failed"] for r in results),
        "total_skipped": sum(r["skipped"] for r in results),
        "suites": results,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Normalized {len(results)} test result files")
    print(f"  Total tests: {summary['total_tests']}")
    print(f"  Passed: {summary['total_passed']}")
    print(f"  Failed: {summary['total_failed']}")
    print(f"  Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Normalize test results")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()
    normalize_results(args.input_dir, args.output)


if __name__ == "__main__":
    main()
