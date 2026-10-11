"""Shared gate plumbing: Rejection result and the REJECT writer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..ledger import Author, Ledger, RecordType

GATES_AUTHOR = Author.code("gates")


@dataclass
class Rejection:
    gate: str  # schema | time | quote | ... (failing_gate on the REJECT record)
    reason: str  # schema_error | capability | unbacked_number | time_leak | quote_not_found | ...
    detail: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:  # a Rejection is truthy, "no rejection" is None
        return True


def write_reject(
    ledger: Ledger, proposal: dict[str, Any], proposal_type: str, rej: Rejection, parents: tuple = ()
) -> str:
    """Append the REJECT record (feeds the kill list) and return its rid."""
    env = ledger.append(
        RecordType.REJECT,
        {
            "proposal": proposal,
            "proposal_type": proposal_type,
            "failing_gate": rej.gate,
            "reason": rej.reason,
            "detail": rej.detail,
        },
        GATES_AUTHOR,
        parents,
    )
    return env.rid


def write_gate_pass(ledger: Ledger, gate: str, subject_rid: str | None, reason: str = "ok") -> str:
    env = ledger.append(
        RecordType.GATE, {"gate": gate, "subject_rid": subject_rid, "result": "pass", "reason": reason}, GATES_AUTHOR
    )
    return env.rid
