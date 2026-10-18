"""Command-line entry point: mt564-bridge convert <input> --out <dir>.

Exit codes: 0 = every message converted (or written unvalidated), 1 = at least one message
rejected or a file failed to parse, 2 = bad configuration or input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .converter import convert_path, count_failures
from .errors import BridgeError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mt564-bridge",
        description="Convert SWIFT MT564 corporate action notifications to ISO 20022 seev.031 XML.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="convert MT564 files or a directory of them")
    convert.add_argument("input", type=Path, help="an MT564 file, or a directory of them")
    convert.add_argument("--out", type=Path, required=True, help="output directory")
    convert.add_argument("--config", type=Path, default=Path("bridge.toml"), help="config file (default: bridge.toml)")
    convert.add_argument(
        "--no-validate",
        action="store_true",
        help="skip XSD validation (development only); reports say written_unvalidated",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        reports = convert_path(args.input, args.out, config, validate=not args.no_validate)
    except BridgeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    failures = 0
    for report in reports:
        failures += _print_report(report)
    return 1 if failures else 0


def _print_report(report: dict) -> int:
    """Print a per-message summary. Returns the number of failures in this file."""
    name = Path(report["source_file"]).name
    if report["file_error"]:
        print(f"{name}: failed to parse: {report['file_error']}", file=sys.stderr)
        return 1
    for message in report["messages"]:
        line = f"{name} message {message['message_index']}: {message['status']}"
        if message["output_file"]:
            line += f" -> {message['output_file']}"
        print(line)
        if message["status"] == "rejected":
            print(f"  reason: {message['error']}", file=sys.stderr)
            for problem in message["validation_errors"]:
                print(f"    {problem}", file=sys.stderr)
    return count_failures(report)
