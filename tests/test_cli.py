from helpers import ROOT, SAMPLES
from mt564_bridge.cli import main


def test_convert_samples_exits_zero(tmp_path, capsys):
    code = main(["convert", str(SAMPLES), "--out", str(tmp_path), "--config", str(ROOT / "bridge.toml"), "--no-validate"])
    assert code == 0
    assert "written_unvalidated" in capsys.readouterr().out


def test_missing_schema_exits_two(tmp_path, capsys):
    code = main(["convert", str(SAMPLES), "--out", str(tmp_path), "--config", str(ROOT / "bridge.toml")])
    assert code == 2
    assert "schema file not found" in capsys.readouterr().err


def test_rejected_message_exits_one(tmp_path, capsys):
    config = tmp_path / "bridge.toml"
    config.write_text(
        '[schema]\nversion = "seev.031.001.16"\nroot_element = "CorpActnNtfctn"\n'
        f'xsd = "{ROOT / "tests" / "fixtures" / "strict.xsd"}"\n\n'
        f'[mapping]\nfile = "{ROOT / "mapping" / "mt564_to_seev031.toml"}"\n',
        encoding="utf-8",
    )
    code = main(["convert", str(SAMPLES / "01_cash_dividend.fin"), "--out", str(tmp_path / "out"), "--config", str(config)])
    assert code == 1
    assert "not expected" in capsys.readouterr().err  # validation detail goes to stderr


def test_bad_config_exits_two(tmp_path, capsys):
    config = tmp_path / "bridge.toml"
    config.write_text('[schema]\nversion = "seev.031.1"\nroot_element = "X"\nxsd = "x"\n[mapping]\nfile = "m"\n', encoding="utf-8")
    code = main(["convert", str(SAMPLES), "--out", str(tmp_path / "out"), "--config", str(config), "--no-validate"])
    assert code == 2
    assert "does not look like seev.031" in capsys.readouterr().err
