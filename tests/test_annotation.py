import io

from hypervariorum.model.annotation import load_annotations
from hypervariorum.nvs.parsing import parse_annotations_to_xml


def test_load_annotations_single_line():
    xml = (
        '<?xml version="1.0"?><annotations>'
        '<annotation act="1" scene="2" line="1">'
        "<lemma>1. [Foo]</lemma><commentary>some commentary</commentary>"
        "</annotation></annotations>"
    )
    annotations = load_annotations(io.StringIO(xml))
    assert len(annotations) == 1
    a = annotations[0]
    assert a.act == 1
    assert a.scene == 2
    assert a.line == 1
    assert a.line_from is None
    assert a.line_to is None
    assert a.is_range is False


def test_load_annotations_line_range():
    xml = (
        '<?xml version="1.0"?><annotations>'
        '<annotation act="1" scene="2" line-from="2" line-to="4">'
        "<lemma>2-4. [Bar]</lemma><commentary>range commentary</commentary>"
        "</annotation></annotations>"
    )
    annotations = load_annotations(io.StringIO(xml))
    a = annotations[0]
    assert a.line is None
    assert a.line_from == 2
    assert a.line_to == 4
    assert a.is_range is True


def test_load_annotations_missing_act_scene():
    xml = (
        '<?xml version="1.0"?><annotations>'
        "<annotation line=\"1\">"
        "<lemma>1. [Foo]</lemma><commentary>no HE seen yet</commentary>"
        "</annotation></annotations>"
    )
    annotations = load_annotations(io.StringIO(xml))
    a = annotations[0]
    assert a.act is None
    assert a.scene is None


def test_load_annotations_quirky_lemma():
    xml = (
        '<?xml version="1.0"?><annotations>'
        '<annotation act="1" scene="2" line="1">'
        "<lemma>1. [Foo</lemma><commentary>some commentary</commentary>"
        "</annotation></annotations>"
    )
    annotations = load_annotations(io.StringIO(xml))
    assert annotations[0].lemma == "1. [Foo"


def test_load_annotations_commentary_whitespace_normalized():
    xml = (
        '<?xml version="1.0"?><annotations>'
        '<annotation act="1" scene="1" line="1"><lemma>1.</lemma>'
        "<commentary>\n      first line\n      second line\n    </commentary>"
        "</annotation></annotations>"
    )
    annotations = load_annotations(io.StringIO(xml))
    assert annotations[0].commentary == "first line\nsecond line"


def test_load_annotations_preserves_order():
    xml = (
        '<?xml version="1.0"?><annotations>'
        '<annotation act="1" scene="1" line="1"><lemma>1.</lemma><commentary>first</commentary></annotation>'
        '<annotation act="1" scene="1" line="2"><lemma>2.</lemma><commentary>second</commentary></annotation>'
        "</annotations>"
    )
    annotations = load_annotations(io.StringIO(xml))
    assert len(annotations) == 2
    assert annotations[0].commentary == "first"
    assert annotations[1].commentary == "second"


def test_load_annotations_empty_document():
    xml = '<?xml version="1.0"?><annotations></annotations>'
    assert load_annotations(io.StringIO(xml)) == []


def test_load_annotations_accepts_path_and_file_object(tmp_path):
    xml = (
        '<?xml version="1.0"?><annotations>'
        '<annotation act="1" scene="1" line="1"><lemma>1.</lemma><commentary>text</commentary></annotation>'
        "</annotations>"
    )
    path = tmp_path / "sample.annot.xml"
    path.write_text(xml)

    from_path = load_annotations(path)
    from_buffer = load_annotations(io.StringIO(xml))

    assert from_path == from_buffer


def test_load_annotations_from_parser_output():
    src = (
        "<HE>Act i, sc. ii.</HE>"
        "<CC><P>1. [Foo] some commentary</CC>"
    )
    xml_out = io.StringIO()
    parse_annotations_to_xml(io.StringIO(src), xml_out)
    xml_out.seek(0)

    annotations = load_annotations(xml_out)

    assert len(annotations) == 1
    a = annotations[0]
    assert a.act == 1
    assert a.scene == 2
    assert a.line == 1
    assert a.lemma == "1. [Foo"
    assert "some commentary" in a.commentary
