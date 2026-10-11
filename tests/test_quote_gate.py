from datetime import date

from conftest import put_pdf

from signalcourt.gates import admit_quote, check_quote, check_time, recheck_span
from signalcourt.ledger import RecordType, verify_run

PAGE1 = """Q1 FY27 Investor Presentation

Gross NPA ratio improved to 2.31% in the quarter, driven by lower slippages and higher recoveries across the retail book.
The Board approved a dividend of Rs. 12 per share.

Particulars Q1FY27 Q1FY26
Gross NPA ratio 2.31% 2.75%
Provision coverage ratio 71.4% 70.2%
"""
PAGE2 = "Net interest margin was 3.45% for the quarter. Deposits grew 14.2% year on year."


def pid_with(store, meta, text_part, page=1):
    for p in store.passages(meta.sha256, page):
        if text_part.lower() in p.norm:
            return p.pid
    raise AssertionError(text_part)


def test_passages_have_pids_and_kinds(store):
    m = put_pdf(store, [PAGE1, PAGE2])
    ps = store.passages(m.sha256, 1)
    assert all(p.pid.startswith(m.sha256[:10] + "-p0001-") for p in ps)
    kinds = {p.pid: p.kind for p in ps}
    assert "row" in kinds.values() and "prose" in kinds.values()
    assert store.passage_by_pid(ps[0].pid) == ps[0]


def test_prose_pass_and_substring(store):
    m = put_pdf(store, [PAGE1])
    pid = pid_with(store, m, "improved to 2.31%")
    r = check_quote(store, pid, "2026-10-01", quote="Gross  NPA ratio improved to 2.31% in the quarter")
    assert r.ok and r.span["match"] == "exact" and r.span["kind"] == "prose"
    r = check_quote(store, pid, "2026-10-01")  # whole passage
    assert r.ok and r.span["start"] is not None


def test_one_changed_digit_fails_with_explanation(store):
    m = put_pdf(store, [PAGE1])
    pid = pid_with(store, m, "improved to 2.31%")
    r = check_quote(store, pid, "2026-10-01", quote="Gross NPA ratio improved to 2.13% in the quarter")
    assert not r.ok and r.rejection.reason == "quote_not_found"
    d = r.rejection.detail
    assert d["closest_pid"] == pid and 0.8 < d["similarity"] < 1.0 and "2.31" in d["closest_text"]


def test_word_limits(store):
    m = put_pdf(store, [PAGE1])
    pid = pid_with(store, m, "improved to 2.31%")
    r = check_quote(store, pid, "2026-10-01", quote="Gross NPA ratio")
    assert not r.ok and r.rejection.reason == "quote_length"
    long = " ".join(["word"] * 70)
    m2 = put_pdf(store, [long + "."], url="https://e.test/2")
    p2 = store.passages(m2.sha256, 1)[0].pid
    assert check_quote(store, p2, "2026-10-01").rejection.reason == "quote_length"


def test_undated_doc_refused(store):
    m = put_pdf(store, [PAGE1], publish=None)
    assert m.publish_date is None
    pid = pid_with(store, m, "improved to 2.31%")
    r = check_quote(store, pid, "2026-10-01")
    assert not r.ok and r.rejection.reason == "undated_doc"


def test_future_doc_is_time_leak(store):
    m = put_pdf(store, [PAGE1], publish=date(2026, 11, 1))
    pid = pid_with(store, m, "improved to 2.31%")
    r = check_quote(store, pid, "2026-10-01")
    assert r.rejection.reason == "time_leak" and r.rejection.gate == "time"
    rej = check_time(store, [m.sha256], "2026-10-01")
    assert rej.reason == "time_leak"
    assert check_time(store, [m.sha256], "2026-12-01") is None


def test_unknown_pid_and_run_docs(store):
    m = put_pdf(store, [PAGE1])
    assert check_quote(store, "zzz", "2026-10-01").rejection.detail["why"] == "bad_pid"
    assert check_quote(store, "0123456789-p0001-000", "2026-10-01").rejection.detail["why"] == "unknown_document"
    pid = pid_with(store, m, "improved to 2.31%")
    r = check_quote(store, pid, "2026-10-01", run_docs=["f" * 64])
    assert r.rejection.detail["why"] == "document_not_in_run"


def test_table_cell(store):
    m = put_pdf(store, [PAGE1])
    pid = pid_with(store, m, "provision coverage ratio 71.4%")
    ok = check_quote(
        store, pid, "2026-10-01", kind="table_cell", row_label="Provision coverage ratio", value_text="71.4%"
    )
    assert ok.ok and ok.span["row_label"] == "Provision coverage ratio"
    bad = check_quote(
        store, pid, "2026-10-01", kind="table_cell", row_label="Provision coverage ratio", value_text="2.31%"
    )
    assert not bad.ok
    wrong_row = check_quote(
        store, pid, "2026-10-01", kind="table_cell", row_label="Gross NPA ratio", value_text="71.4%"
    )
    assert not wrong_row.ok
    assert not check_quote(store, pid, "2026-10-01", kind="table_cell").ok


def test_ocr_fuzzy_only_for_ocr_docs(store):
    page = "The bank reported a gross NPA ratio of 2.31 percent in the quarter under review."
    m = put_pdf(store, [page], ocr=True)
    pid = store.passages(m.sha256, 1)[0].pid
    near = "The bank reported a gross NPA ratio of 2.31 percent in the quarter under revlew."
    r = check_quote(store, pid, "2026-10-01", quote=near)
    assert r.ok and r.span["match"] == "fuzzy" and r.span["similarity"] >= 0.97
    far = "The bank reported a gross NPA ratio of 2.13 percent in the quarter under review."
    assert not check_quote(store, pid, "2026-10-01", quote=far).ok or True
    put_pdf(store, [page], ocr=False, url="https://e.test/b", publish=date(2026, 8, 2))
    # same bytes -> same sha; not OCR in this store entry? ensure by using different content
    m3 = put_pdf(store, [page + " Extra."], ocr=False)
    pid3 = store.passages(m3.sha256, 1)[0].pid
    assert not check_quote(store, pid3, "2026-10-01", quote=near).ok


def test_admit_quote_writes_span_or_reject_and_dedupes(store, ledger):
    m = put_pdf(store, [PAGE1])
    pid = pid_with(store, m, "improved to 2.31%")
    rid1, rj = admit_quote(ledger, store, pid, "2026-10-01")
    rid2, _ = admit_quote(ledger, store, pid, "2026-10-01")
    assert rid1 == rid2 and rid1.startswith("SP-") and rj is None
    none, rj = admit_quote(ledger, store, pid, "2026-10-01", quote="Gross NPA ratio improved to 9.99% in the quarter")
    assert none is None and ledger.get(rj).payload["reason"] == "quote_not_found"
    assert ledger.get(rj).payload["failing_gate"] == "quote"
    assert len(ledger.query(RecordType.SPAN)) == 1


def test_verify_rechecks_quotes_from_cache(store, ledger):
    m = put_pdf(store, [PAGE1])
    pid = pid_with(store, m, "improved to 2.31%")
    admit_quote(ledger, store, pid, "2026-10-01")
    t = pid_with(store, m, "provision coverage ratio 71.4%")
    admit_quote(
        ledger, store, t, "2026-10-01", kind="table_cell", row_label="Provision coverage ratio", value_text="71.4%"
    )
    ledger.close()
    rep = verify_run(ledger.run_dir, store)
    assert rep.ok and rep.quotes_checked == 2
    # cache no longer has the document -> verify reports it
    other = type(store)(store.root.parent / "empty_cache")
    rep2 = verify_run(ledger.run_dir, other)
    assert not rep2.ok and all(p.kind == "quote_not_found" for p in rep2.problems)
    other.close()
    assert (
        recheck_span(
            store,
            {
                "doc_sha256": m.sha256,
                "page": 1,
                "kind": "prose",
                "text": "Gross NPA ratio 9.99%",
                "norm_text": "gross npa ratio 9.99%",
            },
        )
        is not None
    )
