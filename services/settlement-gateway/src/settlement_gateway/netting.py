"""Trade settlement netting for the settlement gateway."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Trade:
    counterparty: str
    currency: str
    direction: str
    amount: Decimal


def _validate(trade: Trade) -> None:
    if trade.direction not in {"pay", "receive"}:
        raise ValueError(f"unknown direction {trade.direction}")
    if trade.amount <= 0:
        raise ValueError("amount must be positive")
    if len(trade.currency) != 3:
        raise ValueError(f"currency {trade.currency} is not an ISO code")


def net_by_counterparty(trades: list[Trade]) -> dict[tuple[str, str], Decimal]:
    """Net a day's trades down to one position per counterparty and currency."""
    if not trades:
        raise ValueError("trades must not be empty")
    positions: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for trade in trades:
        _validate(trade)
        signed = trade.amount if trade.direction == "receive" else -trade.amount
        positions[(trade.counterparty, trade.currency)] += signed
    return dict(positions)


def settlement_instructions(
    positions: dict[tuple[str, str], Decimal]
) -> list[dict[str, str]]:
    """Turn net positions into the payment instructions the gateway emits."""
    instructions = []
    for (counterparty, currency), amount in sorted(positions.items()):
        if amount == 0:
            continue
        instructions.append(
            {
                "counterparty": counterparty,
                "currency": currency,
                "direction": "receive" if amount > 0 else "pay",
                "amount": str(abs(amount)),
            }
        )
    return instructions
