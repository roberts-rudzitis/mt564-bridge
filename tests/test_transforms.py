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


@pytest.mark.parametrize(
    "raw, units, face",
    [("UNIT/2000,", "2000", None), ("FAMT/1000,50", None, "1000.50"), ("UNIT/N15,", "15", None)],
)
def test_units_and_face_amount_return_none_when_not_applicable(raw, units, face):
    unit_value, face_value = TRANSFORMS["units"](raw), TRANSFORMS["face_amount"](raw)
    assert (unit_value.text if unit_value else None) == units
    assert (face_value.text if face_value else None) == face


@pytest.mark.parametrize("raw, expected", [("UNIT/2000,", "LONG"), ("FAMT/N1000,", "SHOR")])
def test_long_short_reads_the_n_sign(raw, expected):
    assert TRANSFORMS["long_short"](raw).text == expected


def test_quantity_rejects_other_types():
    for name in ("units", "face_amount", "long_short"):
        with pytest.raises(ValueError):
            TRANSFORMS[name]("PCS/5")


@pytest.mark.parametrize(
    "raw, completeness, confirmation",
    [("COMP", "COMP", "CONF"), ("COMU", "COMP", "UCON"), ("PREC", "INCO", "CONF"), ("PREU", "INCO", "UCON")],
)
def test_processing_status_pairs(raw, completeness, confirmation):
    assert TRANSFORMS["processing_completeness"](raw).text == completeness
    assert TRANSFORMS["processing_confirmation"](raw).text == confirmation


def test_processing_status_rejects_unknown_codes():
    with pytest.raises(ValueError, match="not supported"):
        TRANSFORMS["processing_completeness"]("ENTL")


def test_security_description_joins_lines_and_skips_when_absent():
    assert TRANSFORMS["security_description"]("ISIN XX1234567897\nSYNTHETIC EQUITY\nCLASS A").text == "SYNTHETIC EQUITY CLASS A"
    assert TRANSFORMS["security_description"]("ISIN XX1234567897") is None
    with pytest.raises(ValueError, match="140"):
        TRANSFORMS["security_description"]("ISIN XX1234567897\n" + "X" * 141)


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
