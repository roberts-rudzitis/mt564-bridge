"""The declarative mapping: load the rule table and apply it to one message.

Rules live in mapping/mt564_to_seev031.toml. This module has no field-specific logic. It
matches each rule to a field, runs the named transform, and records what was mapped,
what was dropped, and what needs a warning.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError, MappingError
from .models import Field, MT564Message
from .transforms import TRANSFORMS, Value

_STATUSES = ("mapped", "partial")


@dataclass(frozen=True)
class Rule:
    """One row of the mapping table."""

    source: str              # MT key, e.g. "98A::PAYD"
    target: str              # XML path below the root element, e.g. "CorpActnDtls/Dt/PmtDt"
    transform: str           # name of a function in transforms.TRANSFORMS
    status: str = "mapped"   # "mapped" or "partial"
    required: bool = False   # True: the message is rejected when the field is missing
    note: str = ""           # the assumption or open question behind the row


@dataclass(frozen=True)
class MappedElement:
    rule: Rule
    field: Field
    value: Value


@dataclass
class MappingResult:
    elements: list[MappedElement] = field(default_factory=list)
    dropped: list[Field] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def load_rules(path: Path) -> list[Rule]:
    """Read and check the rule table. Errors name the rule so the table is easy to fix."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read mapping file {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"mapping file {path} is not valid TOML: {exc}") from exc

    rules: list[Rule] = []
    for number, raw in enumerate(data.get("rule", []), start=1):
        try:
            rule = Rule(**raw)
        except TypeError as exc:
            raise ConfigError(f"rule {number} in {path}: {exc}") from exc
        if rule.transform not in TRANSFORMS:
            raise ConfigError(f"rule {rule.source}: unknown transform {rule.transform!r}")
        if rule.status not in _STATUSES:
            raise ConfigError(f"rule {rule.source}: status must be one of {_STATUSES}")
        rules.append(rule)

    for label, values in (("source", [r.source for r in rules]), ("target", [r.target for r in rules])):
        duplicates = sorted({v for v in values if values.count(v) > 1})
        if duplicates:
            raise ConfigError(f"more than one rule has the same {label}: {duplicates}")
    return rules


def apply_mapping(message: MT564Message, rules: list[Rule]) -> MappingResult:
    """Map one message. Raises MappingError for a missing required field or a bad value."""
    result = MappingResult()
    used_lines: set[int] = set()

    for rule in rules:
        matches = message.find_all(rule.source)
        if not matches:
            if rule.required:
                raise MappingError(f"required field {rule.source} is missing")
            continue

        chosen = matches[0]
        if len(matches) > 1:
            result.warnings.append(
                f"{rule.source} appears {len(matches)} times; only line {chosen.line} is mapped"
            )
        try:
            value = TRANSFORMS[rule.transform](chosen.value)
        except ValueError as exc:
            raise MappingError(f"{rule.source}: {exc}", chosen.line) from exc

        used_lines.add(chosen.line)
        result.elements.append(MappedElement(rule, chosen, value))
        if rule.status == "partial":
            result.warnings.append(f"{rule.source} (line {chosen.line}) is only partly mapped: {rule.note}")

    result.dropped = [f for f in message.fields if f.line not in used_lines]
    return result
