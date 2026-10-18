"""Build the seev.031 XML tree from mapped elements.

The builder knows no ISO 20022 names. It takes each element's path from the mapping
table, creates the parents it needs, and reuses parents it has already created. Children
appear in the order of the mapping table. Element order matters to the XSD, so the table
order is part of the mapping and is checked by validation.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from .mapping import MappedElement


def build_document(elements: list[MappedElement], namespace: str, root_element: str) -> ET.Element:
    """Return a Document element containing the root element and the mapped content."""
    ET.register_namespace("", namespace)
    document = ET.Element(_tag(namespace, "Document"))
    root = ET.SubElement(document, _tag(namespace, root_element))
    nodes: dict[tuple[str, ...], ET.Element] = {(): root}

    for element in elements:
        *parents, leaf = element.rule.target.split("/")
        for depth in range(1, len(parents) + 1):
            key = tuple(parents[:depth])
            if key not in nodes:
                nodes[key] = ET.SubElement(nodes[key[:-1]], _tag(namespace, parents[depth - 1]))
        child = ET.SubElement(nodes[tuple(parents)], _tag(namespace, leaf), element.value.attrs)
        child.text = element.value.text
    return document


def to_xml_bytes(document: ET.Element) -> bytes:
    """Serialise with indentation and an XML declaration, encoded as UTF-8."""
    ET.indent(document, space="  ")
    return ET.tostring(document, encoding="UTF-8", xml_declaration=True)


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"
