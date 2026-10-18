"""Value transforms, referenced by name from the mapping table.

A transform receives the raw MT value (the text after the qualifier) and returns a
Value, or raises ValueError with a plain reason. They are pure functions, so each one
can be tested on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable


@dataclass
class Value:
    """A converted value: element text plus optional XML attributes."""

    text: str
    attrs: dict[str, str] = field(default_factory=dict)


_MT_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
_CODE = re.compile(r"^[A-Z]{4}$")
_NUMBER = re.compile(r"^\d+(,\d+)?$")
_AMOUNT = re.compile(r"^([A-Z]{3})(\d+(?:,\d+)?)$")
_QUANTITY = re.compile(r"^(?:FAMT|UNIT)/(\d+(?:,\d*)?)$")
_SUPPORTED_FUNCTIONS = ("NEWM", "REPL")


def plain(raw: str) -> Value:
    """Free text: strip surrounding whitespace."""
    return Value(raw.strip())


def code(raw: str) -> Value:
    """A four-letter code. Whether the code exists in the ISO code list is left to XSD validation."""
    text = raw.strip()
    if not _CODE.match(text):
        raise ValueError(f"expected a four-letter code, got {text!r}")
    return Value(text)


def function_code(raw: str) -> Value:
    """Function of the message. v1 supports NEWM and REPL only."""
    text = raw.strip()
    if text not in _SUPPORTED_FUNCTIONS:
        supported = ", ".join(_SUPPORTED_FUNCTIONS)
        raise ValueError(f"function {text!r} is not supported in v1 (supported: {supported})")
    return Value(text)


def mt_date(raw: str) -> Value:
    """MT dates are YYYYMMDD. ISO 20022 uses YYYY-MM-DD."""
    text = raw.strip()
    match = _MT_DATE.match(text)
    if not match:
        raise ValueError(f"expected a date as YYYYMMDD, got {text!r}")
    try:
        return Value(date(*map(int, match.groups())).isoformat())
    except ValueError:
        raise ValueError(f"{text!r} is not a real calendar date") from None


def isin(raw: str) -> Value:
    """The ISIN is on the first line of :35B:, optionally after the word ISIN.

    Later lines hold the security description, which v1 does not map.
    """
    tokens = raw.split("\n", 1)[0].split()
    if tokens[:1] == ["ISIN"]:
        tokens = tokens[1:]
    if not tokens or not _ISIN.match(tokens[0]):
        raise ValueError("expected 'ISIN' followed by a 12-character ISIN")
    return Value(tokens[0])


def rate(raw: str) -> Value:
    """MT rates use a comma as the decimal separator. ISO uses a point."""
    text = raw.strip()
    if not _NUMBER.match(text):
        raise ValueError(f"expected a rate such as 0,25, got {text!r}")
    return Value(text.replace(",", "."))


def amount(raw: str) -> Value:
    """A currency code and an amount, e.g. EUR1000,00. The currency becomes the Ccy attribute."""
    match = _AMOUNT.match(raw.strip())
    if not match:
        raise ValueError(f"expected a currency and an amount such as EUR1000,00, got {raw.strip()!r}")
    return Value(match.group(2).replace(",", "."), {"Ccy": match.group(1)})


def quantity(raw: str) -> Value:
    """FAMT/ (face amount) or UNIT/ (units) followed by a quantity such as UNIT/2000,.

    Both types become the same number in v1. The distinction is recorded as a warning.
    """
    match = _QUANTITY.match(raw.strip())
    if not match:
        raise ValueError(f"expected FAMT/ or UNIT/ followed by a quantity, got {raw.strip()!r}")
    return Value(match.group(1).rstrip(",").replace(",", "."))


TRANSFORMS: dict[str, Callable[[str], Value]] = {
    "plain": plain,
    "code": code,
    "function": function_code,
    "date": mt_date,
    "isin": isin,
    "rate": rate,
    "amount": amount,
    "quantity": quantity,
}
