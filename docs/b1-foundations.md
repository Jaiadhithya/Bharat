# B1 Foundations (ledger, store, gates)

Python 3.10-compatible (tested on 3.10.20). Layout mirrors `signalcourt/` in implementation.md section 3;
B0 owns the repo skeleton, so merge these three packages and `tests/` into it unchanged.

- `signalcourt/ledger/`: `canonical.py` (D15 hash), `schema.py` (24 record types, capability table, payload models), `store.py` (`Ledger`), `verify.py` (`verify_run`; CALC recompute is an injected callable because the calculator is B2's).
- `signalcourt/store/`: `DocStore` facade (`put_bytes`, `meta`, `read_bytes`, `pages`, `passages`), `blobs`, `manifest`, `text` (PyMuPDF, passages with pids), `normalise`, `dates`, `timegate`.
- `signalcourt/gates/`: `check_proposal`/`check_schema` (schema, capability, unbacked numbers), `check_time`, `check_quote`/`admit_quote`/`recheck_span`, `Rejection`, `write_reject`.

Runtime deps used: pydantic>=2, ftfy, rapidfuzz, pymupdf, python-dateutil. Test deps: pytest, hypothesis.

Notes for other threads
- Capability is checked before schema. The `Author.writer` (role if set, else component) must be in `CAPABILITIES[type]`: roles investigator/advocate/redteam for EVIDENCE etc.; components calculator, prereg, scheduler, judge, writer, router, gates, quote_gate, extract, resolve, harvest/tools, sensors/ranker, forensics, angle_planner, controller.
- rid = prefix + first 8 hex of the record hash (longer on a collision). The rid and hash are excluded from the hashed bytes.
- `prereg_head` seq = last CLAIM; EVIDENCE/CHALLENGE/REBUTTAL need a CLAIM with seq <= it. REBUTTAL is checked via its CHALLENGE's claim.
- Quote gate reasons: `quote_not_found` (detail has closest_pid/closest_text/similarity), `quote_length`, `undated_doc`; `time_leak` is gate `time`.
- `exempt_small_counts` (default False) on the unbacked-number check exempts bare integers 0-10; spec is strict, so call sites decide.
