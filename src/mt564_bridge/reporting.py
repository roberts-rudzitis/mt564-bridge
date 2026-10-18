"""Conversion reports. One JSON file per input file, with one entry per message."""

from __future__ import annotations

import json
from pathlib import Path

from .mapping import MappedElement
from .models import Field


def mapped_entry(element: MappedElement) -> dict:
    return {
        "mt_field": element.rule.source,
        "line": element.field.line,
        "xml_path": element.rule.target,
        "value": element.value.text,
        "status": element.rule.status,
    }


def dropped_entry(field: Field) -> dict:
    return {
        "mt_field": field.key,
        "line": field.line,
        "value": field.value,
        "reason": "no rule in the mapping table (not supported in v1)",
    }


def write_report(path: Path, report: dict) -> None:
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
