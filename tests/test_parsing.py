import io

from hypervariorum.nvs.parsing import parse_annotations_to_xml, roman_to_int


def test_roman_to_int_basic():
    assert roman_to_int("i") == "1"
    assert roman_to_int("iv") == "4"
    assert roman_to_int("ix") == "9"
    assert roman_to_int("xl") == "40"


def test_roman_to_int_case_insensitive_and_whitespace():
    assert roman_to_int(" III ") == "3"
    assert roman_to_int("vii") == "7"


def test_parse_annotations_to_xml_tracks_act_and_scene():
    src = (
        "<HE>Act i, sc. ii.</HE>"
        "<CC><P>1. [Foo] some commentary</CC>"
    )
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(src), out)
    xml = out.getvalue()
    assert '<annotation act="1" scene="2" line="1">' in xml
    assert "<lemma>1. [Foo</lemma>" in xml
    assert "some commentary" in xml


def test_parse_annotations_to_xml_line_range():
    src = "<CC><P>2-4. [Bar] range commentary</CC>"
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(src), out)
    xml = out.getvalue()
    assert 'line-from="2" line-to="4"' in xml


def test_parse_annotations_to_xml_wraps_in_annotations_element():
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(""), out)
    xml = out.getvalue()
    assert xml.startswith('<?xml version="1.0" encoding="utf-8"?>\n<annotations>\n')
    assert xml.endswith("</annotations>\n")
