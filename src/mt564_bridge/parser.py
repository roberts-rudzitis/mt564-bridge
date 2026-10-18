"""Parse MT564 text into MT564Message objects.

An MT message is a series of blocks: {1:...}{2:...}{3:...}{4:<text>-}. We split the
file at each block 1 marker, read blocks 1 and 2 for routing, then walk block 4 line
by line. A line that starts with :TAG: opens a new field. Any other line continues the
field above it. Sequence markers :16R:NAME and :16S:NAME group the fields.
"""

from __future__ import annotations

import re

from .errors import ParseError
from .models import Field, MT564Message

_BLOCK1 = re.compile(r"\{1:([^}]*)\}")
_BLOCK2 = re.compile(r"\{2:([^}]*)\}")
_BLOCK4_START = re.compile(r"\{4:\r?\n")
_BLOCK4_END = re.compile(r"\r?\n-\}")
_SEQ_OPEN = re.compile(r"^:16R:([A-Z]{3,8})$")
_SEQ_CLOSE = re.compile(r"^:16S:([A-Z]{3,8})$")
_FIELD = re.compile(r"^:(\d{2}[A-Z]?):(.*)$")
_QUALIFIER = re.compile(r"^:([A-Z0-9]{1,4})//(.*)$")


def parse_file(text: str) -> list[MT564Message]:
    """Return every message in `text`, in file order."""
    starts = [m.start() for m in re.finditer(r"\{1:", text)]
    if not starts:
        raise ParseError("no block 1 found; this is not an MT message")
    ends = starts[1:] + [len(text)]
    return [
        _parse_message(text, start, end, index)
        for index, (start, end) in enumerate(zip(starts, ends), start=1)
    ]


def _parse_message(text: str, start: int, end: int, index: int) -> MT564Message:
    chunk = text[start:end]
    first_line = _line_of(text, start)

    block1 = _BLOCK1.match(chunk)
    if block1 is None or len(block1.group(1)) < 15:
        raise ParseError("block 1 is missing or too short", first_line)
    sender = block1.group(1)[3:15]  # logical terminal address, after "F01"

    block2 = _BLOCK2.search(chunk)
    if block2 is None or len(block2.group(1)) < 16:
        raise ParseError("block 2 is missing or too short", first_line)
    header = block2.group(1)
    if header[1:4] != "564":
        line = _line_of(text, start + block2.start())
        raise ParseError(f"block 2 has message type {header[1:4]}, expected 564", line)
    receiver = header[4:16]

    body_start = _BLOCK4_START.search(chunk)
    if body_start is None:
        raise ParseError("block 4 is missing", first_line)
    body_end = _BLOCK4_END.search(chunk, body_start.end())
    if body_end is None:
        raise ParseError("block 4 is not closed with -}", first_line)

    body_line = _line_of(text, start + body_start.end())
    fields = _parse_block4(chunk[body_start.end():body_end.start()], body_line)
    return MT564Message(index=index, sender=sender, receiver=receiver, fields=fields)


def _parse_block4(body: str, first_line: int) -> list[Field]:
    """Group block 4 lines into fields, tracking the open sequence."""
    raw: list[list] = []  # [tag, text, line, sequence], filled in file order
    sequence: str | None = None

    for offset, line in enumerate(body.split("\n")):
        line = line.rstrip("\r")
        lineno = first_line + offset
        if not line:
            continue
        if match := _SEQ_OPEN.match(line):
            if sequence is not None:
                raise ParseError(f"sequence {match.group(1)} opens inside sequence {sequence}", lineno)
            sequence = match.group(1)
        elif match := _SEQ_CLOSE.match(line):
            if match.group(1) != sequence:
                raise ParseError(
                    f"sequence {match.group(1)} closes but {sequence or 'no sequence'} is open", lineno
                )
            sequence = None
        elif match := _FIELD.match(line):
            raw.append([match.group(1), match.group(2), lineno, sequence])
        elif line.startswith(":"):
            raise ParseError(f"malformed field tag {line[:12]!r}", lineno)
        elif raw:
            raw[-1][1] += "\n" + line  # continuation of the previous field
        else:
            raise ParseError("text found before the first field", lineno)

    if sequence is not None:
        raise ParseError(f"sequence {sequence} is never closed", first_line)
    return [_to_field(*item) for item in raw]


def _to_field(tag: str, text: str, line: int, sequence: str | None) -> Field:
    """Split ':PAYD//20261105' into qualifier and value. Fields without '//' have no qualifier."""
    qualified = _QUALIFIER.match(text)
    if qualified:
        return Field(tag, qualified.group(1), qualified.group(2), line, sequence)
    return Field(tag, None, text, line, sequence)


def _line_of(text: str, position: int) -> int:
    """1-based line number of a character position."""
    return text.count("\n", 0, position) + 1
