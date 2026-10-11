"""Gate 2: every cited DOC must be `ok` under the Time Gate, else REJECT time_leak."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ..store.timegate import allowed
from .common import Rejection


def check_time(store, doc_shas: Iterable[str], as_of: str | date) -> Rejection | None:
    """None if every cited document is published on or before as_of.

    Undated documents pass here (they may be read for definitions); the quote gate refuses
    to turn them into EVIDENCE spans.
    """
    leaks = []
    for sha in doc_shas:
        if not store.has(sha):
            return Rejection("time", "unknown_document", {"sha256": sha})
        m = store.meta(sha)
        if allowed(m, as_of) == "dropped":
            leaks.append({"sha256": sha, "publish_date": m.publish_date})
    if leaks:
        return Rejection("time", "time_leak", {"as_of": str(as_of), "documents": leaks})
    return None
