"""XSD validation with lxml. The schema file is never bundled; bridge.toml points at it."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from .errors import ConfigError


def load_schema(xsd_path: Path) -> etree.XMLSchema:
    """Load the XSD, or stop with a message that says what to do."""
    if not xsd_path.is_file():
        raise ConfigError(
            f"schema file not found: {xsd_path}. Place the official XSD there, "
            "or run with --no-validate for development."
        )
    try:
        return etree.XMLSchema(etree.parse(str(xsd_path)))
    except etree.LxmlError as exc:
        raise ConfigError(f"schema file {xsd_path} could not be loaded: {exc}") from exc


def validate_xml(xml_bytes: bytes, schema: etree.XMLSchema) -> list[str]:
    """Return one readable string per schema error. An empty list means valid."""
    document = etree.fromstring(xml_bytes)
    if schema.validate(document):
        return []
    return [f"line {error.line}: {error.message}" for error in schema.error_log]
