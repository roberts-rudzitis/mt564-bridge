import pytest

from helpers import BASE, SAMPLES, make_mt
from mt564_bridge.errors import ParseError
from mt564_bridge.parser import parse_file


def test_fields_keep_tag_qualifier_sequence_and_line():
    text = (SAMPLES / "01_cash_dividend.fin").read_text(encoding="utf-8")
    message = parse_file(text)[0]
    caev = message.find("22F::CAEV")
    assert caev.value == "DVCA"
    assert caev.sequence == "GENL"
    assert caev.line == text.splitlines().index(":22F::CAEV//DVCA") + 1


def test_qualifier_is_split_from_value():
    message = parse_file(make_mt(BASE))[0]
    payd = message.find("98A::PAYD")
    assert (payd.tag, payd.qualifier, payd.value) == ("98A", "PAYD", "20261105")


def test_continuation_lines_join_the_field_above():
    message = parse_file(make_mt(BASE))[0]
    assert message.find("35B").value == "ISIN XX1234567897\nSYNTHETIC EQUITY ALPHA"


def test_sender_and_receiver_come_from_blocks_1_and_2():
    message = parse_file(make_mt(BASE, sender="AAAABBBBXXXX", receiver="CCCCDDDDEEEE"))[0]
    assert message.sender == "AAAABBBBXXXX"
    assert message.receiver == "CCCCDDDDEEEE"


def test_two_messages_in_one_file_are_both_parsed():
    text = (SAMPLES / "03_redemptions_two_messages.fin").read_text(encoding="utf-8")
    messages = parse_file(text)
    assert [m.index for m in messages] == [1, 2]
    assert messages[0].find("22F::CAEV").value == "REDM"
    assert messages[1].find("22F::CAEV").value == "PRED"


def test_missing_optional_field_is_simply_absent():
    text = (SAMPLES / "04_voluntary_tender.fin").read_text(encoding="utf-8")
    message = parse_file(text)[0]
    assert message.find("98A::RDTE") is None
    assert message.find("98A::PAYD") is not None


@pytest.mark.parametrize(
    "text, expected, line",
    [
        ("no blocks here", "no block 1 found", None),
        ("{1:F01SYNTH}{2:I564SYNTHCUSTXXXN}{4:\n-}", "block 1 is missing or too short", 1),
        ("{1:F01SYNTHBANKAXX0000000000}{4:\n-}", "block 2 is missing or too short", 1),
        (make_mt(BASE, block2_type="103"), "message type 103, expected 564", 1),
        ("{1:F01SYNTHBANKAXX0000000000}{2:I564SYNTHCUSTXXXN}", "block 4 is missing", 1),
        (
            "{1:F01SYNTHBANKAXX0000000000}{2:I564SYNTHCUSTXXXN}{4:\n:20C::SEME//X\n",
            "block 4 is not closed",
            1,
        ),
        (make_mt([":16R:GENL", ":ABC:bad", ":16S:GENL"]), "malformed field tag", 3),
        (make_mt([":16R:GENL", ":16R:USECU"]), "opens inside sequence GENL", 3),
        (make_mt([":16R:GENL", ":16S:USECU"]), "closes but GENL is open", 3),
        (make_mt([":16R:GENL", ":20C::SEME//X"]), "sequence GENL is never closed", 2),
        (make_mt(["hello", ":20C::SEME//X"]), "text found before the first field", 2),
    ],
)
def test_malformed_input_raises_with_line(text, expected, line):
    with pytest.raises(ParseError, match=expected) as info:
        parse_file(text)
    assert info.value.line == line
