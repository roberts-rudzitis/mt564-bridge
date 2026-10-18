from xml.etree import ElementTree as ET

from mt564_bridge.mapping import MappedElement, Rule
from mt564_bridge.models import Field
from mt564_bridge.transforms import Value
from mt564_bridge.xml_builder import build_document, to_xml_bytes

NS = "urn:iso:std:iso:20022:tech:xsd:seev.031.001.16"


def _element(target, text, attrs=None):
    rule = Rule(source="X", target=target, transform="plain")
    return MappedElement(rule, Field("99A", None, "x", 1, None), Value(text, attrs or {}))


def _local(tag):
    return tag.split("}", 1)[1]


def test_root_and_document_wrapper_use_the_namespace():
    doc = build_document([], NS, "CorpActnNtfctn")
    assert doc.tag == f"{{{NS}}}Document"
    assert doc[0].tag == f"{{{NS}}}CorpActnNtfctn"


def test_shared_parents_are_created_once():
    doc = build_document([_element("A/B/C", "1"), _element("A/B/D", "2")], NS, "Root")
    parent = doc.find(f"{{{NS}}}Root/{{{NS}}}A/{{{NS}}}B")
    assert [_local(child.tag) for child in parent] == ["C", "D"]
    assert len(doc.findall(f".//{{{NS}}}B")) == 1


def test_attributes_and_text_are_written():
    doc = build_document([_element("Amt", "10.00", {"Ccy": "EUR"})], NS, "Root")
    amount = doc.find(f"{{{NS}}}Root/{{{NS}}}Amt")
    assert amount.text == "10.00"
    assert amount.get("Ccy") == "EUR"


def test_serialised_xml_declares_the_default_namespace():
    data = to_xml_bytes(build_document([_element("A", "1")], NS, "Root"))
    assert data.startswith(b"<?xml")
    assert f'<Document xmlns="{NS}">'.encode() in data
