"""Entry point used by the regulatory-reporting pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reporting import ReportBuilder  # noqa: E402

LEDGER = {"US-SEC": 8421, "EU-ESMA": 12903, "UK-FCA": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--compliance-level", default="standard")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    records = ReportBuilder(args.compliance_level).build(LEDGER, args.date)
    for record in records:
        path = os.path.join(args.output_dir, f"{record.jurisdiction.lower()}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record.as_dict(), handle, indent=2)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
