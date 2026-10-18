"""The pipeline: input file, then messages, then mapping, then XML, then validation, then report.

Three rules keep the output honest:
* A message is written only if it maps cleanly and passes validation.
* Every MT field appears in the report, either as mapped or as dropped with its line.
* A message that fails is reported with its errors, and no XML is written for it.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .errors import BridgeError, MappingError, ParseError
from .mapping import Rule, apply_mapping, load_rules
from .models import MT564Message
from .parser import parse_file
from .reporting import dropped_entry, mapped_entry, write_report
from .validation import load_schema, validate_xml
from .xml_builder import build_document, to_xml_bytes

_INPUT_SUFFIXES = {".fin", ".txt", ".mt564"}


def collect_inputs(path: Path) -> list[Path]:
    """A single file, or every MT564 file in a directory (sorted by name)."""
    if path.is_file():
        return [path]
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in _INPUT_SUFFIXES)
        if not files:
            raise BridgeError(f"no MT564 files ({', '.join(sorted(_INPUT_SUFFIXES))}) found in {path}")
        return files
    raise BridgeError(f"input not found: {path}")


def convert_path(input_path: Path, out_dir: Path, config: Config, validate: bool = True) -> list[dict]:
    """Convert every input file. Returns one report per input file and writes each report to out_dir."""
    files = collect_inputs(input_path)
    rules = load_rules(config.mapping_path)
    schema = load_schema(config.xsd_path) if validate else None  # fail before writing anything
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    for file in files:
        report = convert_file(file, out_dir, config, rules, schema)
        write_report(out_dir / f"{file.stem}.report.json", report)
        reports.append(report)
    return reports


def convert_file(path: Path, out_dir: Path, config: Config, rules: list[Rule], schema) -> dict:
    report: dict = {
        "source_file": str(path),
        "schema_version": config.schema_version,
        "validated": schema is not None,
        "file_error": None,
        "messages": [],
    }
    try:
        messages = parse_file(path.read_text(encoding="utf-8"))
    except (ParseError, UnicodeDecodeError) as exc:
        report["file_error"] = str(exc)
        return report
    report["messages"] = [
        convert_message(message, path, out_dir, config, rules, schema) for message in messages
    ]
    return report


def convert_message(
    message: MT564Message, path: Path, out_dir: Path, config: Config, rules: list[Rule], schema
) -> dict:
    entry: dict = {
        "message_index": message.index,
        "sender": message.sender,
        "receiver": message.receiver,
        "status": "rejected",
        "output_file": None,
        "error": None,
        "mapped": [],
        "dropped": [],
        "warnings": [],
        "validation_errors": [],
    }
    try:
        mapping = apply_mapping(message, rules)
    except MappingError as exc:
        entry["error"] = str(exc)
        return entry

    entry["mapped"] = [mapped_entry(e) for e in mapping.elements]
    entry["dropped"] = [dropped_entry(f) for f in mapping.dropped]
    entry["warnings"] = mapping.warnings

    xml_bytes = to_xml_bytes(build_document(mapping.elements, config.namespace, config.root_element))
    if schema is None:
        status = "written_unvalidated"
    else:
        errors = validate_xml(xml_bytes, schema)
        if errors:
            entry["validation_errors"] = errors
            entry["error"] = "XSD validation failed; no XML written"
            return entry
        status = "converted"

    out_file = out_dir / f"{path.stem}_msg{message.index:02d}.seev031.xml"
    out_file.write_bytes(xml_bytes)
    entry.update(status=status, output_file=str(out_file))
    return entry


def count_failures(report: dict) -> int:
    """Number of messages that were rejected, or 1 if the whole file failed to parse."""
    if report["file_error"]:
        return 1
    return sum(1 for m in report["messages"] if m["status"] == "rejected")
