"""Plain data classes for a parsed MT564. Nothing here knows about XML or ISO 20022."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    """One MT field from block 4, for example :98A::PAYD//20261105."""

    tag: str                 # "98A"
    qualifier: str | None    # "PAYD", or None when the field has no qualifier
    value: str               # text after the qualifier; continuation lines joined with "\n"
    line: int                # 1-based line number where the field starts
    sequence: str | None     # "GENL", "USECU" and so on; None outside any sequence

    @property
    def key(self) -> str:
        """Lookup key used by the mapping table, e.g. "98A::PAYD" or "23G"."""
        return f"{self.tag}::{self.qualifier}" if self.qualifier else self.tag


@dataclass
class MT564Message:
    """One MT564 message: routing from blocks 1 and 2, then the block 4 fields in order."""

    index: int               # 1-based position within the input file
    sender: str
    receiver: str
    fields: list[Field] = field(default_factory=list)

    def find(self, key: str) -> Field | None:
        """The first field with this key, or None."""
        return next((f for f in self.fields if f.key == key), None)

    def find_all(self, key: str) -> list[Field]:
        """Every field with this key, in file order."""
        return [f for f in self.fields if f.key == key]
