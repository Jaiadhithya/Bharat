import hashlib

import pytest

from signalcourt.ledger.canonical import GENESIS_HASH, canonical_json, compute_hash


def test_key_order_irrelevant():
    assert canonical_json({"b": 1, "a": [1, {"d": 2, "c": 3}]}) == canonical_json({"a": [1, {"c": 3, "d": 2}], "b": 1})


def test_format_and_unicode():
    assert canonical_json({"a": "₹ é"}) == '{"a":"₹ é"}'.encode()


def test_floats_rounded_nan_none():
    assert canonical_json({"x": 0.1 + 0.2}) == b'{"x":0.3}'
    assert canonical_json({"x": float("nan")}) == b'{"x":null}'
    assert canonical_json({"x": -0.0}) == canonical_json({"x": 0.0})
    assert canonical_json({"x": float("inf")}) == b'{"x":null}'


def test_rejects_non_json_types():
    with pytest.raises(TypeError):
        canonical_json({"x": {1, 2}})
    with pytest.raises(TypeError):
        canonical_json({1: "a"})


def test_genesis():
    assert GENESIS_HASH == hashlib.sha256(b"signal-court/v2").hexdigest()


def test_d15_hash_formula_and_excluded_fields():
    env = {"seq": 1, "type": "RUN", "payload": {"a": 1}}
    expected = hashlib.sha256(GENESIS_HASH.encode() + canonical_json(env)).hexdigest()
    assert compute_hash(GENESIS_HASH, env) == expected
    # hash and rid are never part of the hashed bytes
    assert compute_hash(GENESIS_HASH, dict(env, hash="zz", rid="RN-00000000")) == expected
    assert compute_hash("0" * 64, env) != expected
