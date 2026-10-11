from signalcourt.gates import CitedValue, check_finding_text, check_proposal, cited_values_from_ledger, find_unbacked
from signalcourt.ledger import Author, RecordType

C = CitedValue


def bad(text, *cited, **kw):
    return [b.token for b in find_unbacked(text, cited, **kw)]


def test_percent_and_fraction():
    c = C("CA-1", 0.0231, "fraction")
    assert bad("GNPA fell to 2.31%", c) == []
    assert bad("GNPA fell to 2.3%", c) == []  # display rounding, +-1 last digit
    assert bad("GNPA fell to 2.4%", c) == []
    assert bad("GNPA fell to 2.5%", c) == ["2.5%"]
    assert bad("GNPA fell to 2.31 %", c) == []
    assert bad("fell 231 bps", C("CA-1", 0.0231, "fraction")) == []
    assert bad("fell by 50 bps", C("CA-2", -0.005, "fraction")) == []  # sign ignored, direction is text


def test_pp_units():
    assert bad("gap of 2.1 pp", C("CA-1", 2.1, "pp")) == []
    assert bad("gap of 210 bps", C("CA-1", 2.1, "pp")) == []
    assert bad("gap of 2.1%", C("CA-1", 2.1, "pp")) == []


def test_crore_and_bn_and_x():
    c = C("FA-1", 12345.6, "inr_cr")
    assert bad("advances of 12,345.6 cr", c) == []
    assert bad("advances of 12,345 crore", c) == bad("advances of 12,345 crore", c)  # 12,345 vs 12345.6: off by .6 < 1
    assert bad("advances of 123.5 bn", c) == []
    assert bad("advances of 99 cr", c) == ["99 cr"]
    assert bad("coverage of 1.4x", C("CA-3", 1.4, "ratio")) == []


def test_unbacked_when_nothing_cited():
    assert bad("NIM rose to 3.45%") == ["3.45%"]
    assert bad("no numbers here") == []


def test_exempt_dates_years_quarters_ids():
    t = (
        "On 11 Oct 2026 and 2026-10-11, in Q2 FY27 (FY2027, Q1FY26), see EV-3f9a1c2b and "
        "0123456789-p0004-012; the 3rd quarter of 2025 and 24/07/2026."
    )
    assert bad(t) == []


def test_small_counts_option():
    assert bad("three of 4 peers") == ["4"]
    assert bad("three of 4 peers", exempt_small_counts=True) == []
    assert bad("5%", exempt_small_counts=True) == ["5%"]


def test_year_like_numbers_with_units_not_exempt():
    assert bad("deposits of 2024 cr") == ["2024 cr"]


def test_ledger_integration_proposal_check(ledger):
    Author(component="x", role="investigator")
    calc = ledger.append(
        RecordType.CALC,
        {
            "formula_id": "yoy",
            "formula_version": 1,
            "formula_text": "t",
            "inputs": [],
            "value": 0.142,
            "unit": "fraction",
            "recon_status": "pass",
        },
        Author.code("calculator"),
    )
    assert [c.value for c in cited_values_from_ledger(ledger, [calc.rid, "XX-nope"])] == [0.142]
    claim = ledger.append(
        RecordType.CLAIM,
        {
            "hypothesis_index": 1,
            "statement": "s",
            "mechanism": "m",
            "signal_rid": "SG-00000000",
            "falsification": {
                "metric": "m",
                "comparator": ">",
                "threshold": 1,
                "deadline_period": "Q4FY27",
                "source_rule": "r",
            },
            "drafter": {"model": "x", "family": "f"},
        },
        Author.code("prereg"),
    )
    ledger.seal_head("prereg_head")
    ch = {"claim_rid": claim.rid, "alt_type": "sector", "severity": "minor", "evidence": [], "calc": [calc.rid]}
    ok, rej = check_proposal(
        ledger,
        RecordType.CHALLENGE,
        dict(ch, argument="Deposits grew 14.2% so the sector moved."),
        Author(component="x", role="redteam"),
    )
    assert ok is not None and rej is None
    ok, rej = check_proposal(
        ledger,
        RecordType.CHALLENGE,
        dict(ch, argument="Deposits grew 19.9% so the sector moved."),
        Author(component="x", role="redteam"),
    )
    assert ok is None and rej.reason == "unbacked_number" and rej.detail["tokens"][0]["token"] == "19.9%"
    # capability rejection
    ok, rej = check_proposal(
        ledger, RecordType.CHALLENGE, dict(ch, argument="x"), Author(component="x", role="advocate")
    )
    assert rej.reason == "capability"
    # schema rejection
    ok, rej = check_proposal(
        ledger, RecordType.CHALLENGE, {"claim_rid": claim.rid}, Author(component="x", role="redteam")
    )
    assert rej.reason == "schema_error"


def test_finding_text_uses_item_rids(ledger):
    calc = ledger.append(
        RecordType.CALC,
        {
            "formula_id": "f",
            "formula_version": 1,
            "formula_text": "t",
            "inputs": [],
            "value": 31.5,
            "unit": "pp",
            "recon_status": "pass",
        },
        Author.code("calculator"),
    )

    def item(t, rids):
        return {"text": t, "rids": rids}

    el = {
        "discovery": item("Gap widened to 31.5 pp.", [calc.rid]),
        "why": [item("It is 31.5 pp wide.", [calc.rid])],
        "counterargument": item("Peers show 8 pp.", [calc.rid]),
    }
    assert check_finding_text(ledger, {"elements": el}).detail["tokens"][0]["token"] == "8 pp"
    el["counterargument"] = item("Peers show nothing.", [])
    assert check_finding_text(ledger, {"elements": el}) is None
