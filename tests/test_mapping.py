import pytest

from helpers import BASE, ROOT, SAMPLES, make_mt
from mt564_bridge.errors import ConfigError, MappingError
from mt564_bridge.mapping import apply_mapping, load_rules
from mt564_bridge.parser import parse_file


def _first_message(text):
    return parse_file(text)[0]


def _map(config, text):
    return apply_mapping(_first_message(text), load_rules(config.mapping_path))


def test_dividend_sample_maps_every_field(config):
    text = (SAMPLES / "01_cash_dividend.fin").read_text(encoding="utf-8")
    result = _map(config, text)
    values = {e.rule.target: e.value.text for e in result.elements}
    assert values["CorpActnDtls/Dt/PmtDt"] == "2026-11-05"
    assert values["CorpActnDtls/RateDtls/GrssRate"] == "0.25"
    assert values["AcctsListAndBalDtls/SfkpgAcct"] == "SYNACC000123"
    assert result.dropped == []


def test_currency_becomes_attribute_on_cash_amount(config):
    text = (SAMPLES / "01_cash_dividend.fin").read_text(encoding="utf-8")
    amounts = [e for e in _map(config, text).elements if e.rule.target == "CorpActnDtls/CshPmt/Amt"]
    assert amounts[0].value.attrs == {"Ccy": "EUR"}


def test_partial_rules_add_warnings(config):
    text = (SAMPLES / "01_cash_dividend.fin").read_text(encoding="utf-8")
    warnings = _map(config, text).warnings
    assert any(w.startswith("35B (line") and "only partly mapped" in w for w in warnings)


def test_unknown_field_is_dropped_with_its_line(config):
    text = make_mt(BASE + [":70E::ADTX//SYNTHETIC NARRATIVE"])
    result = _map(config, text)
    # BASE fills block 4 lines 2 to 16, so the appended field is on line 17.
    assert [(f.key, f.line) for f in result.dropped] == [("70E::ADTX", 2 + len(BASE))]


def test_repeated_field_maps_first_and_drops_the_rest(config):
    text = make_mt(BASE + [":98A::PAYD//20261106"])
    result = _map(config, text)
    assert any("appears 2 times" in w for w in result.warnings)
    assert [f.line for f in result.dropped] == [2 + len(BASE)]


def test_missing_required_field_rejects_message(config):
    lines = [line for line in BASE if not line.startswith(":35B") and line != "SYNTHETIC EQUITY ALPHA"]
    with pytest.raises(MappingError, match="required field 35B is missing"):
        _map(config, make_mt(lines))


def test_bad_value_rejects_message_with_line(config):
    lines = [line.replace(":98A::PAYD//20261105", ":98A::PAYD//20261340") for line in BASE]
    with pytest.raises(MappingError, match="not a real calendar date") as info:
        _map(config, make_mt(lines))
    assert info.value.line == 7


def test_missing_optional_field_is_not_an_error(config):
    text = (SAMPLES / "04_voluntary_tender.fin").read_text(encoding="utf-8")
    result = _map(config, text)
    assert all(e.rule.source != "98A::RDTE" for e in result.elements)


def test_mapping_doc_lists_every_rule(config):
    doc = (ROOT / "docs" / "mapping.md").read_text(encoding="utf-8")
    for rule in load_rules(config.mapping_path):
        assert f"`{rule.source}`" in doc, rule.source
        assert f"`{rule.target}`" in doc, rule.target


def test_load_rules_rejects_unknown_transform(tmp_path):
    path = tmp_path / "m.toml"
    path.write_text('[[rule]]\nsource = "23G"\ntarget = "A"\ntransform = "nope"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown transform"):
        load_rules(path)


def test_load_rules_rejects_duplicate_target(tmp_path):
    path = tmp_path / "m.toml"
    path.write_text(
        '[[rule]]\nsource = "23G"\ntarget = "A"\ntransform = "plain"\n'
        '[[rule]]\nsource = "35B"\ntarget = "A"\ntransform = "plain"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="same target"):
        load_rules(path)


def test_load_rules_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="cannot read mapping file"):
        load_rules(tmp_path / "missing.toml")
