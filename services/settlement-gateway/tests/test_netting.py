import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from settlement_gateway.netting import (  # noqa: E402
    Trade,
    net_by_counterparty,
    settlement_instructions,
)


def trade(counterparty="ACME", currency="USD", direction="pay", amount="100"):
    return Trade(counterparty, currency, direction, Decimal(amount))


def test_offsetting_trades_net_to_zero():
    positions = net_by_counterparty(
        [trade(direction="pay", amount="100"), trade(direction="receive", amount="100")]
    )
    assert positions[("ACME", "USD")] == Decimal("0")


def test_positions_are_split_by_currency():
    positions = net_by_counterparty(
        [trade(currency="USD", amount="100"), trade(currency="EUR", amount="40")]
    )
    assert positions[("ACME", "USD")] == Decimal("-100")
    assert positions[("ACME", "EUR")] == Decimal("-40")


def test_zero_positions_produce_no_instruction():
    positions = {("ACME", "USD"): Decimal("0"), ("BETA", "GBP"): Decimal("25")}
    assert settlement_instructions(positions) == [
        {
            "counterparty": "BETA",
            "currency": "GBP",
            "direction": "receive",
            "amount": "25",
        }
    ]


def test_instructions_report_the_paying_side():
    instructions = settlement_instructions({("ACME", "USD"): Decimal("-12.50")})
    assert instructions[0]["direction"] == "pay"
    assert instructions[0]["amount"] == "12.50"


def test_empty_trades_are_rejected():
    with pytest.raises(ValueError):
        net_by_counterparty([])


@pytest.mark.parametrize(
    "kwargs",
    [{"direction": "settle"}, {"amount": "0"}, {"currency": "DOLLAR"}],
)
def test_invalid_trades_are_rejected(kwargs):
    with pytest.raises(ValueError):
        net_by_counterparty([trade(**kwargs)])
