import json
from dataclasses import replace

import pytest

from helpers import BASE, FIXTURES, SAMPLES, make_mt
from mt564_bridge.converter import convert_path
from mt564_bridge.errors import BridgeError


def _messages(reports):
    return [m for report in reports for m in report["messages"]]


def test_samples_convert_without_validation(tmp_path, config):
    reports = convert_path(SAMPLES, tmp_path, config, validate=False)
    messages = _messages(reports)
    assert len(reports) == 4
    assert len(messages) == 5
    assert {m["status"] for m in messages} == {"written_unvalidated"}
    assert len(list(tmp_path.glob("*.seev031.xml"))) == 5


def test_report_is_written_as_json_with_mapped_and_dropped(tmp_path, config):
    convert_path(SAMPLES / "01_cash_dividend.fin", tmp_path, config, validate=False)
    report = json.loads((tmp_path / "01_cash_dividend.report.json").read_text(encoding="utf-8"))
    assert report["validated"] is False
    message = report["messages"][0]
    assert {"mt_field", "xml_path", "line"} <= set(message["mapped"][0])
    assert [d["mt_field"] for d in message["dropped"]] == ["92A::GRSS", "19A::CASH"]


def test_samples_validate_against_official_xsd(tmp_path, config):
    if not config.xsd_path.is_file():
        pytest.skip(f"official XSD not present at {config.xsd_path}; see schemas/README.md")
    reports = convert_path(SAMPLES, tmp_path, config, validate=True)
    assert {m["status"] for m in _messages(reports)} == {"converted"}


def test_rejected_message_writes_no_xml(tmp_path, config):
    strict = replace(config, xsd_path=FIXTURES / "strict.xsd")
    reports = convert_path(SAMPLES / "01_cash_dividend.fin", tmp_path, strict, validate=True)
    message = reports[0]["messages"][0]
    assert message["status"] == "rejected"
    assert message["output_file"] is None
    assert message["validation_errors"]
    assert "no XML written" in message["error"]
    assert list(tmp_path.glob("*.xml")) == []


def test_accepted_message_is_written(tmp_path, config):
    accept = replace(config, xsd_path=FIXTURES / "accept_any.xsd")
    reports = convert_path(SAMPLES / "02_rights_distribution_replacement.fin", tmp_path, accept, validate=True)
    message = reports[0]["messages"][0]
    assert message["status"] == "converted"
    assert (tmp_path / "02_rights_distribution_replacement_msg01.seev031.xml").is_file()


def test_mapping_error_is_reported_not_raised(tmp_path, config):
    source = tmp_path / "bad_date.fin"
    lines = [line.replace(":98A::PAYD//20261105", ":98A::PAYD//20261340") for line in BASE]
    source.write_text(make_mt(lines), encoding="utf-8")
    reports = convert_path(source, tmp_path / "out", config, validate=False)
    message = reports[0]["messages"][0]
    assert message["status"] == "rejected"
    assert "not a real calendar date" in message["error"]


def test_malformed_file_is_reported_as_file_error(tmp_path, config):
    source = tmp_path / "broken.fin"
    source.write_text("{1:F01SYNTHBANKAXX0000000000}{2:I564SYNTHCUSTXXXN}{4:\n:20C::SEME//X\n", encoding="utf-8")
    reports = convert_path(source, tmp_path / "out", config, validate=False)
    assert reports[0]["file_error"] and "not closed" in reports[0]["file_error"]
    assert reports[0]["messages"] == []


def test_empty_directory_is_an_error(tmp_path, config):
    with pytest.raises(BridgeError, match="no MT564 files"):
        convert_path(tmp_path, tmp_path / "out", config, validate=False)


def test_missing_input_is_an_error(tmp_path, config):
    with pytest.raises(BridgeError, match="input not found"):
        convert_path(tmp_path / "nope.fin", tmp_path / "out", config, validate=False)
