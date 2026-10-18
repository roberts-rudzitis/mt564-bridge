import pytest

from mt564_bridge.transforms import TRANSFORMS


@pytest.mark.parametrize("raw, expected", [("20261105", "2026-11-05"), ("20240229", "2024-02-29")])
def test_date_converts_yyyymmdd(raw, expected):
    assert TRANSFORMS["date"](raw).text == expected


@pytest.mark.parametrize("raw", ["2026110", "20261340", "20230229", "abcd1234"])
def test_date_rejects_bad_values(raw):
    with pytest.raises(ValueError):
        TRANSFORMS["date"](raw)


@pytest.mark.parametrize("raw, expected", [("ISIN XX1234567897\nDESC", "XX1234567897"), ("XX1234567897", "XX1234567897")])
def test_isin_takes_first_line(raw, expected):
    assert TRANSFORMS["isin"](raw).text == expected


@pytest.mark.parametrize("raw", ["ISIN ABCDEFGHIJKL", "ISIN XX123", ""])
def test_isin_rejects_bad_values(raw):
    with pytest.raises(ValueError):
        TRANSFORMS["isin"](raw)


def test_rate_uses_point_decimal():
    assert TRANSFORMS["rate"]("0,25").text == "0.25"
    with pytest.raises(ValueError):
        TRANSFORMS["rate"]("abc")


def test_amount_carries_currency_as_attribute():
    value = TRANSFORMS["amount"]("EUR1000,00")
    assert (value.text, value.attrs) == ("1000.00", {"Ccy": "EUR"})
    for bad in ("1000", "EU1000,00"):
        with pytest.raises(ValueError):
            TRANSFORMS["amount"](bad)


@pytest.mark.parametrize("raw, expected", [("UNIT/2000,", "2000"), ("FAMT/1000,50", "1000.50")])
def test_quantity_accepts_unit_and_face_amount(raw, expected):
    assert TRANSFORMS["quantity"](raw).text == expected


def test_quantity_rejects_other_types():
    with pytest.raises(ValueError):
        TRANSFORMS["quantity"]("PCS/5")


def test_code_checks_shape_only():
    assert TRANSFORMS["code"]("ZZZZ").text == "ZZZZ"  # shape is fine; the XSD decides if it exists
    with pytest.raises(ValueError):
        TRANSFORMS["code"]("dvca")


def test_function_supports_only_v1_codes():
    assert TRANSFORMS["function"]("NEWM").text == "NEWM"
    assert TRANSFORMS["function"]("REPL").text == "REPL"
    with pytest.raises(ValueError, match="not supported in v1"):
        TRANSFORMS["function"]("RMDR")


def test_plain_strips_whitespace():
    assert TRANSFORMS["plain"]("  SYN564  ").text == "SYN564"
