import pytest

from helpers import FIXTURES
from mt564_bridge.errors import ConfigError
from mt564_bridge.validation import load_schema, validate_xml
from mt564_bridge.xml_builder import build_document, to_xml_bytes

NS = "urn:iso:std:iso:20022:tech:xsd:seev.031.001.16"


def _document_bytes():
    return to_xml_bytes(build_document([], NS, "CorpActnNtfctn"))


def test_missing_schema_file_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="schema file not found"):
        load_schema(tmp_path / "absent.xsd")


def test_unparseable_schema_is_a_config_error(tmp_path):
    bad = tmp_path / "bad.xsd"
    bad.write_text("this is not a schema", encoding="utf-8")
    with pytest.raises(ConfigError, match="could not be loaded"):
        load_schema(bad)


def test_valid_document_has_no_errors():
    schema = load_schema(FIXTURES / "accept_any.xsd")
    assert validate_xml(_document_bytes(), schema) == []


def test_invalid_document_reports_line_and_message():
    schema = load_schema(FIXTURES / "strict.xsd")
    errors = validate_xml(_document_bytes(), schema)
    assert errors and errors[0].startswith("line ")
    assert "not expected" in errors[0]
