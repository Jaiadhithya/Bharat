from datetime import date

import pytest

from signalcourt.store.dates import date_from_page_text, parse_pdf_date, resolve_publish_date
from signalcourt.store.timegate import allowed, audit_max_publish_date


def test_broadcast_wins():
    r = resolve_publish_date(
        broadcast_ts="2026-07-24 17:45:03",
        pdf_creation="D:20260701",
        period_end=date(2026, 6, 30),
        page1_text="Date: 1 Jan 2020",
        url="x/20200101.pdf",
    )
    assert (r.date, r.source) == (date(2026, 7, 24), "exchange_broadcast")


def test_pdf_metadata_only_within_window():
    pe = date(2026, 6, 30)
    assert resolve_publish_date(pdf_creation="D:20260724120000+05'30'", period_end=pe).source == "pdf_metadata"
    assert resolve_publish_date(pdf_creation="D:20260601", period_end=pe).source == "none"  # before period end
    assert resolve_publish_date(pdf_creation="D:20261101", period_end=pe).source == "none"  # > 120 days
    assert resolve_publish_date(pdf_creation="D:20260724").source == "none"  # no period_end


def test_page_text_then_url():
    r = resolve_publish_date(page1_text="Results\nDate: 24 July 2026\nBody")
    assert (r.date, r.source) == (date(2026, 7, 24), "page_text")
    assert resolve_publish_date(url="https://x/files/20260724_deck.pdf").date == date(2026, 7, 24)
    assert resolve_publish_date(url="https://x/files/24072026_deck.pdf").date == date(2026, 7, 24)
    assert resolve_publish_date(url="https://x/a.pdf").source == "none"


def test_helpers():
    assert parse_pdf_date("D:2026") == date(2026, 1, 1)
    assert parse_pdf_date("junk") is None
    assert date_from_page_text("nothing here") is None


def test_timegate():
    assert allowed({"publish_date": "2026-09-30"}, "2026-10-01") == "ok"
    assert allowed({"publish_date": "2026-10-01"}, date(2026, 10, 1)) == "ok"
    assert allowed({"publish_date": "2026-10-02"}, "2026-10-01") == "dropped"
    assert allowed({"publish_date": None}, "2026-10-01") == "undated"
    audit_max_publish_date([{"publish_date": "2026-09-01"}], "2026-10-01")
    with pytest.raises(AssertionError):
        audit_max_publish_date([{"publish_date": "2026-11-01"}], "2026-10-01")
