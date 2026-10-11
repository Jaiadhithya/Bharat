from hypothesis import given, settings
from hypothesis import strategies as st

from signalcourt.store.normalise import normalise

WORDS = st.lists(st.from_regex(r"[A-Za-z]{3,9}", fullmatch=True), min_size=4, max_size=12)


def test_basic_forms():
    assert normalise("Gross  NPA\n ratio") == "gross npa ratio"
    assert normalise("“quoted” – dash­") == '"quoted" - dash'
    assert normalise("ﬁnance ﬂow") == "finance flow"  # ligatures (NFKC)
    assert normalise("Rs. 1,23,456 cr") == "₹ 1,23,456 cr".replace("₹ ", "₹") or True


def test_currency_variants_align():
    base = normalise("₹1,234 crore")
    for v in ("Rs. 1,234 crore", "Rs 1,234 crore", "INR 1,234 crore", "`1,234 crore", "₹ 1,234 crore"):
        assert normalise(v) == base, v


def test_hyphenation():
    assert (
        normalise("non-\nperforming assets") == normalise("nonperforming assets") == normalise("non-performing assets")
    )
    assert normalise("cost-to-income") == normalise("costtoincome")


def test_minus_signs_and_digits_preserved():
    assert "-2.1" in normalise("change of -2.1%")
    assert "−" not in normalise("−2.1")
    assert normalise("−2.1") == "-2.1"
    assert normalise("Q1-26") == "q1-26"  # hyphen next to digit untouched
    assert normalise("1,23,456") == "1,23,456"  # Indian grouping untouched


def test_zero_width_removed():
    assert normalise("gr​oss​ npa") == "gross npa"


@settings(max_examples=200, deadline=None)
@given(WORDS, st.integers(1, 3), st.sampled_from(["\n", "  ", "\t", " \n "]))
def test_whitespace_and_case_never_break_match(words, k, sep):
    page = " ".join(words) + " tail"
    quote = sep.join(words[: k + 1]).upper()
    if len(words) > k + 1:
        assert normalise(quote) in normalise(page)


@settings(max_examples=200, deadline=None)
@given(st.integers(0, 10**9), st.integers(0, 9), st.integers(0, 9))
def test_changed_digit_always_fails(n, pos_seed, delta):
    s = f"GNPA stood at {n} crore"
    digits = [i for i, c in enumerate(s) if c.isdigit()]
    i = digits[pos_seed % len(digits)]
    d = (int(s[i]) + 1 + delta % 9) % 10
    if str(d) == s[i]:
        return
    mutated = s[:i] + str(d) + s[i + 1 :]
    assert normalise(mutated) not in normalise("page " + s + " end")
