import io
import xml.etree.ElementTree as ET

from hypervariorum.nvs.parsing import (
    parse_annotations_to_xml,
    parse_lemma,
    roman_to_int,
    split_annotation_chunks,
)


def test_roman_to_int_basic():
    assert roman_to_int("i") == "1"
    assert roman_to_int("iv") == "4"
    assert roman_to_int("ix") == "9"
    assert roman_to_int("xl") == "40"


def test_roman_to_int_case_insensitive_and_whitespace():
    assert roman_to_int(" III ") == "3"
    assert roman_to_int("vii") == "7"


def test_parse_lemma_plain_numbered():
    lemma, commentary = parse_lemma("1. some commentary")
    assert lemma == "1."
    assert commentary == "some commentary"


def test_parse_lemma_bracketed():
    lemma, commentary = parse_lemma("1. [Foo] some commentary")
    assert lemma == "1. [Foo"
    assert commentary == "some commentary"


def test_parse_lemma_bracketed_with_bold_tag():
    lemma, commentary = parse_lemma("2. <B>Foo]</B> some commentary")
    assert lemma == "2. <B>Foo</B>"
    assert commentary == "some commentary"


def test_parse_lemma_bracketed_no_leading_number():
    lemma, commentary = parse_lemma("[Foo] some commentary")
    assert lemma == "[Foo"
    assert commentary == "some commentary"


def test_parse_lemma_range():
    lemma, commentary = parse_lemma("2-4. [Bar] range commentary")
    assert lemma == "2-4. [Bar"
    assert commentary == "range commentary"


def test_parse_lemma_no_match_returns_empty_lemma():
    lemma, commentary = parse_lemma("plain commentary with no lemma marker")
    assert lemma == ""
    assert commentary == "plain commentary with no lemma marker"


def test_split_annotation_chunks_splits_on_p_boundaries():
    # A leading empty chunk is expected here: cc_inner always starts with the
    # first <P>, and the split pattern matches at position 0. The orchestrator
    # filters it out via `if not chunk: continue`.
    chunks = split_annotation_chunks("<P>1. [Foo] first<P>2. [Bar] second")
    assert chunks == ["", "1. [Foo] first", "2. [Bar] second"]


def test_parse_annotations_to_xml_tracks_act_and_scene():
    src = (
        "<HE>Act i, sc. ii.</HE>"
        "<CC><P>1. [Foo] some commentary</CC>"
    )
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(src), out)
    root = ET.fromstring(out.getvalue())

    annotation = root.find("annotation")
    assert annotation.get("act") == "1"
    assert annotation.get("scene") == "2"
    assert annotation.get("line") == "1"
    assert annotation.findtext("lemma") == "1. [Foo"
    assert "some commentary" in annotation.findtext("commentary")


def test_parse_annotations_to_xml_line_range():
    src = "<CC><P>2-4. [Bar] range commentary</CC>"
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(src), out)
    root = ET.fromstring(out.getvalue())

    annotation = root.find("annotation")
    assert annotation.get("line-from") == "2"
    assert annotation.get("line-to") == "4"


def test_parse_annotations_to_xml_wraps_in_annotations_element():
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(""), out)
    root = ET.fromstring(out.getvalue())

    assert root.tag == "annotations"
    assert list(root) == []


def test_parse_annotations_to_xml_escapes_special_characters():
    src = "<CC><P>1. [Rowe & Pope] commentary with <stray> markup</CC>"
    out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(src), out)
    xml = out.getvalue()

    root = ET.fromstring(xml)
    annotation = root.find("annotation")
    assert "Rowe & Pope" in annotation.findtext("lemma")
    assert "<stray>" in annotation.findtext("commentary")
