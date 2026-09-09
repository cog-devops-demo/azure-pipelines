"""Report construction for the weekday compliance run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

JURISDICTIONS = ("US-SEC", "EU-ESMA", "UK-FCA")


@dataclass(frozen=True)
class ReportRecord:
    jurisdiction: str
    report_date: str
    compliance_level: str
    trade_count: int
    exceptions: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "jurisdiction": self.jurisdiction,
            "reportDate": self.report_date,
            "complianceLevel": self.compliance_level,
            "tradeCount": self.trade_count,
            "exceptions": list(self.exceptions),
        }


class ReportBuilder:
    """Builds one record per jurisdiction from a trade ledger."""

    def __init__(self, compliance_level: str) -> None:
        if compliance_level not in ("standard", "elevated"):
            raise ValueError(f"unknown compliance level: {compliance_level}")
        self.compliance_level = compliance_level

    def build(self, ledger: dict[str, int], report_date: str | None = None) -> list[ReportRecord]:
        report_date = report_date or date.today().isoformat()
        records = []
        for jurisdiction in JURISDICTIONS:
            count = ledger.get(jurisdiction, 0)
            exceptions = ()
            if count == 0:
                exceptions = ("no-trades-reported",)
            elif self.compliance_level == "elevated" and count > 10_000:
                exceptions = ("volume-threshold-exceeded",)
            records.append(
                ReportRecord(
                    jurisdiction=jurisdiction,
                    report_date=report_date,
                    compliance_level=self.compliance_level,
                    trade_count=count,
                    exceptions=exceptions,
                )
            )
        return records
