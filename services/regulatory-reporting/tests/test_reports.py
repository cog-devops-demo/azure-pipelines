import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest  # noqa: E402

from reporting import ReportBuilder  # noqa: E402


def test_builds_one_record_per_jurisdiction():
    records = ReportBuilder("elevated").build({"US-SEC": 10}, "2026-01-05")
    assert [r.jurisdiction for r in records] == ["US-SEC", "EU-ESMA", "UK-FCA"]


def test_empty_jurisdiction_is_flagged():
    records = ReportBuilder("standard").build({"US-SEC": 10}, "2026-01-05")
    empty = [r for r in records if r.trade_count == 0]
    assert all("no-trades-reported" in r.exceptions for r in empty)


def test_elevated_volume_threshold():
    records = ReportBuilder("elevated").build({"US-SEC": 20_000}, "2026-01-05")
    us = next(r for r in records if r.jurisdiction == "US-SEC")
    assert us.exceptions == ("volume-threshold-exceeded",)


def test_standard_level_ignores_volume_threshold():
    records = ReportBuilder("standard").build({"US-SEC": 20_000}, "2026-01-05")
    us = next(r for r in records if r.jurisdiction == "US-SEC")
    assert us.exceptions == ()


def test_unknown_compliance_level_rejected():
    with pytest.raises(ValueError):
        ReportBuilder("bogus")
