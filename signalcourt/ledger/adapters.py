"""Adapters that let other modules write to the ledger through their own narrow ports."""

from __future__ import annotations

from typing import Any

from .schema import Author, RecordType
from .store import Ledger

CALCULATOR = Author.code("calculator")


class LedgerCalcSink:
    """Implements ``calc.calculator.CalcSink``: append a CALC record and return its rid.

    The payload is validated by the ledger, so a calculator that drifts from the CALC schema
    fails loudly instead of writing a malformed record.
    """

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def append_calc(self, payload: dict[str, Any], parents: list[str]) -> str:
        return self.ledger.append(RecordType.CALC, payload, CALCULATOR, parents).rid
