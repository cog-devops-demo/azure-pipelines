#!/usr/bin/env python3
"""
Summarize build results across all services for migration validation.

Generates a summary report showing which services have been validated,
which have baseline mismatches, and which are pending migration.
"""

import argparse
import json
import os
from pathlib import Path


SERVICES = [
    "pricing-engine",
    "portfolio-api",
    "risk-batch",
    "market-sim",
    "ops-control-plane",
    "frontend-workbench",
    "regulatory-reporting",
    "notebook-executor",
    "scenario-runner",
]


def summarize(baselines_dir: str, results_dir: str = None) -> dict:
    """Generate a summary of all service validation status."""
    baselines_path = Path(baselines_dir)
    summary = {
        "services": {},
        "totals": {
            "total": len(SERVICES),
            "has_baseline": 0,
            "missing_baseline": 0,
            "validated": 0,
            "pending": 0,
        },
    }

    for service in SERVICES:
        service_baseline = baselines_path / service / "expected-artifacts.json"
        has_baseline = service_baseline.exists()

        service_info = {
            "has_baseline": has_baseline,
            "validated": False,
            "status": "pending",
        }

        if has_baseline:
            summary["totals"]["has_baseline"] += 1
            with open(service_baseline) as f:
                baseline = json.load(f)
                service_info["artifact_name"] = baseline.get("artifact_name")
                service_info["last_updated"] = baseline.get("last_updated")
        else:
            summary["totals"]["missing_baseline"] += 1
            service_info["status"] = "no_baseline"

        summary["services"][service] = service_info

    summary["totals"]["pending"] = (
        summary["totals"]["total"] - summary["totals"]["validated"]
    )

    return summary


def main():
    parser = argparse.ArgumentParser(description="Summarize build validation results")
    parser.add_argument("--baselines", required=True, help="Path to baselines directory")
    parser.add_argument("--results", help="Path to validation results directory")
    parser.add_argument("--output", help="Output path for summary report")

    args = parser.parse_args()

    summary = summarize(args.baselines, args.results)
    print(json.dumps(summary, indent=2))

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
