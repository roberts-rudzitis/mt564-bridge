"""Value transforms, referenced by name from the mapping table.

A transform receives the raw MT value (the text after the qualifier) and returns a
Value, or raises ValueError with a plain reason. A transform may also return None when
the field does not apply to its target (for example a UNIT quantity for the FaceAmt
element); the rule is then skipped. They are pure functions, so each one can be tested
on its own.
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
_QUANTITY = re.compile(r"^(FAMT|UNIT)/(N?)(\d+(?:,\d*)?)$")
_SUPPORTED_FUNCTIONS = ("NEWM", "REPL")

# 25D::PROC processing status -> seev.031 PrcgSts/Cd (event completeness, event confirmation).
# The pairs follow common market practice for MT564 -> seev.031; see docs/mapping.md.
_PROCESSING_STATUS = {
    "COMP": ("COMP", "CONF"),  # complete, confirmed
    "COMU": ("COMP", "UCON"),  # complete, unconfirmed
    "PREC": ("INCO", "CONF"),  # preliminary, confirmed
    "PREU": ("INCO", "UCON"),  # preliminary, unconfirmed
}


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


def _processing_status(raw: str) -> tuple[str, str]:
    text = raw.strip()
    if text not in _PROCESSING_STATUS:
        supported = ", ".join(_PROCESSING_STATUS)
        raise ValueError(f"processing status {text!r} is not supported (supported: {supported})")
    return _PROCESSING_STATUS[text]


def event_completeness(raw: str) -> Value:
    """25D::PROC -> COMP (complete) or INCO (preliminary)."""
    return Value(_processing_status(raw)[0])


def event_confirmation(raw: str) -> Value:
    """25D::PROC -> CONF (confirmed) or UCON (unconfirmed)."""
    return Value(_processing_status(raw)[1])


def isin(raw: str) -> Value:
    """The ISIN is on the first line of :35B:, optionally after the word ISIN."""
    tokens = raw.split("\n", 1)[0].split()
    if tokens[:1] == ["ISIN"]:
        tokens = tokens[1:]
    if not tokens or not _ISIN.match(tokens[0]):
        raise ValueError("expected 'ISIN' followed by a 12-character ISIN")
    return Value(tokens[0])


def security_description(raw: str) -> Value | None:
    """The lines after the ISIN line of :35B:, joined with spaces. None when there are none."""
    lines = [line.strip() for line in raw.split("\n")[1:] if line.strip()]
    if not lines:
        return None
    text = " ".join(lines)
    if len(text) > 140:  # Max140Text in seev.031
        raise ValueError(f"security description is longer than 140 characters ({len(text)})")
    return Value(text)


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


def _quantity(raw: str) -> tuple[str, bool, str]:
    """Split a balance such as UNIT/2000, or FAMT/N1500,5 into (type, is_short, number)."""
    match = _QUANTITY.match(raw.strip())
    if not match:
        raise ValueError(f"expected FAMT/ or UNIT/ followed by a quantity, got {raw.strip()!r}")
    kind, sign, number = match.groups()
    return kind, sign == "N", number.rstrip(",").replace(",", ".")


def long_short(raw: str) -> Value:
    """MT marks a short (negative) balance with N after the slash. ISO uses SHOR or LONG."""
    return Value("SHOR" if _quantity(raw)[1] else "LONG")


def units(raw: str) -> Value | None:
    """The quantity of a UNIT/ balance; None for a face amount."""
    kind, _, number = _quantity(raw)
    return Value(number) if kind == "UNIT" else None


def face_amount(raw: str) -> Value | None:
    """The quantity of a FAMT/ balance; None for units."""
    kind, _, number = _quantity(raw)
    return Value(number) if kind == "FAMT" else None


# rate and amount are not used by the v1 table: in seev.031 rates and cash amounts belong to the
# option details (MT sequence E), which v1 does not map. They are kept for that next step.
TRANSFORMS: dict[str, Callable[[str], Value | None]] = {
    "plain": plain,
    "code": code,
    "function": function_code,
    "date": mt_date,
    "processing_completeness": event_completeness,
    "processing_confirmation": event_confirmation,
    "isin": isin,
    "security_description": security_description,
    "long_short": long_short,
    "units": units,
    "face_amount": face_amount,
    "rate": rate,
    "amount": amount,
}
