import io

from lxml import etree

from hypervariorum.model.annotation import load_annotations
from hypervariorum.nvs.parsers import (
    Chunk,
    ChunkConsolidator,
    RawtoChunks,
    parse_inline_markup,
    parse_lemma,
    roman_to_int,
    split_annotation_chunks,
)


def _write(tmp_path, content):
    file_path = tmp_path / "raw.txt"
    file_path.write_text(content)
    return file_path


def test_parse_extracts_multiline_cc_block(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<CC><P>1. some commentary\n"
        "that continues on the next line.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert len(parser.chunks) == 1
    assert "<P>1. some commentary\nthat continues on the next line." in parser.chunks[0].content
    assert "</CC>" not in parser.chunks[0].content


def test_parse_extracts_single_line_cc_block_without_swallowing_next_chunk(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<CC><P>101. <B>should]</B> See III, iv, 25.</CC>\n"
        "<CC><P>2. second annotation.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert len(parser.chunks) == 2
    assert "101." in parser.chunks[0].content
    assert "second annotation" not in parser.chunks[0].content
    assert "second annotation" in parser.chunks[1].content


def test_parse_excludes_content_outside_cc_tags(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<PB N=4>\n"
        "some stray running text that is not commentary\n"
        "<CC><P>1. actual commentary.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert len(parser.chunks) == 1
    assert "stray running text" not in parser.chunks[0].content
    assert "<PB" not in parser.chunks[0].content


def test_parse_excludes_content_outside_start_stop_markers(tmp_path):
    src = (
        "<CC><P>0. before start, should be excluded.</CC>\n"
        "<!-- START -->\n"
        "<CC><P>1. inside markers.</CC>\n"
        "<!-- STOP -->\n"
        "<CC><P>2. after stop, should be excluded.</CC>\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert len(parser.chunks) == 1
    assert "inside markers" in parser.chunks[0].content


def test_parse_with_no_start_marker_produces_no_chunks(tmp_path):
    src = "<CC><P>1. no markers at all.</CC>\n"
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert parser.chunks == []


def test_parse_head_recto_extracts_page_act_scene():
    parser = RawtoChunks(None)
    result = parser.parse_head("<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>")

    assert result["page_number"] == 4
    assert result["act"] == "1"
    assert result["scene"] == "1"


def test_parse_head_verso_extracts_page_act_scene():
    parser = RawtoChunks(None)
    result = parser.parse_head("<HE><SC>act i, sc.</SC> i.] <I>KING LEAR</I> 5</HE>")

    assert result["page_number"] == 5
    assert result["act"] == "1"
    assert result["scene"] == "1"


def test_parse_head_unmatched_header_returns_empty_dict(caplog):
    parser = RawtoChunks(None)
    result = parser.parse_head("<HE>vi <I>PREFACE</I></HE>")

    assert result == {}


def test_parse_carries_page_act_scene_onto_chunk(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<CC><P>1. commentary.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert parser.chunks[0].page_number == 4
    assert parser.chunks[0].act == "1"
    assert parser.chunks[0].scene == "1"


def test_parse_chunk_before_any_header_has_no_act_scene_page(tmp_path):
    src = (
        "<!-- START -->\n"
        "<CC><P>1. commentary with no preceding header.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert parser.chunks[0].act is None
    assert parser.chunks[0].scene is None
    assert parser.chunks[0].page_number is None


def test_serialize_writes_chunks_wrapped_in_root_element(tmp_path):
    parser = RawtoChunks(tmp_path / "unused.txt")
    parser.chunks = [
        Chunk(act=None, scene=None, page_number=4, content="first"),
        Chunk(act=None, scene=None, page_number=5, content="second"),
    ]

    out_path = tmp_path / "out.xml"
    parser.serialize(out_path)

    written = out_path.read_text()
    assert written.startswith("<chunks>\n")
    assert written.rstrip().endswith("</chunks>")
    assert "<chunk page_number='4'>first</chunk>" in written
    assert "<chunk page_number='5'>second</chunk>" in written


# --- migrated from tests/test_parsing.py (functions copied into parsers.py) ---

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
    # first <P>, and the split pattern matches at position 0. The consumer
    # filters it out via `if not part: continue`.
    chunks = split_annotation_chunks("<P>1. [Foo] first<P>2. [Bar] second")
    assert chunks == ["", "1. [Foo] first", "2. [Bar] second"]


# --- parse_inline_markup ---

def test_parse_inline_markup_bare_tag_becomes_hi_element():
    parent = etree.Element("lemma")
    parse_inline_markup("<SC>Walker</SC>", parent)

    assert len(parent) == 1
    hi = parent[0]
    assert hi.tag == "hi"
    assert hi.get("rend") == "smallcaps"
    assert hi.text == "Walker"
    assert not parent.text
    assert not hi.tail


def test_parse_inline_markup_mixed_content_distributes_text_and_tail():
    parent = etree.Element("commentary")
    parse_inline_markup("foo <B>bar</B> baz", parent)

    assert parent.text == "foo "
    assert len(parent) == 1
    hi = parent[0]
    assert hi.get("rend") == "bold"
    assert hi.text == "bar"
    assert hi.tail == " baz"


def test_parse_inline_markup_entities_survive_as_literal_text():
    parent = etree.Element("commentary")
    text = "‘Tender-hefted’ — no tags here"
    parse_inline_markup(text, parent)

    assert parent.text == text
    assert len(parent) == 0


def test_parse_inline_markup_unrecognized_tag_passes_through():
    parent = etree.Element("commentary")
    parse_inline_markup("<BQ>quoted</BQ>", parent)

    assert parent.text == "<BQ>quoted</BQ>"
    assert len(parent) == 0


def test_parse_inline_markup_real_lemma_with_bold():
    # raw/shake.var.lear.txt: "2. <B>Albany]</B> ..."
    parent = etree.Element("lemma")
    parse_inline_markup("2. <B>Albany]</B>", parent)

    assert parent.text == "2. "
    hi = parent[0]
    assert hi.get("rend") == "bold"
    assert hi.text == "Albany]"
    assert not hi.tail


def test_parse_inline_markup_real_commentary_with_smallcaps():
    # raw/shake.var.lear.txt: "<SC>Walker</SC> (<I>Crit.</I> i, 13) ..."
    parent = etree.Element("commentary")
    parse_inline_markup("<SC>Walker</SC> (<I>Crit.</I> i, 13)", parent)

    assert len(parent) == 2
    walker, crit = parent
    assert walker.get("rend") == "smallcaps"
    assert walker.text == "Walker"
    assert walker.tail == " ("
    assert crit.get("rend") == "italic"
    assert crit.text == "Crit."
    assert crit.tail == " i, 13)"


# --- ChunkConsolidator ---

def test_consolidate_normal_chunk_produces_annotations():
    chunk = Chunk(act="1", scene="2", page_number=4,
                  content="<P>1. [Foo] some commentary<P>2. [Bar] more")
    consolidator = ChunkConsolidator([chunk])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 2
    a1, a2 = consolidator.annotations
    assert a1.act == 1
    assert a1.scene == 2
    assert a1.line == 1
    assert a1.lemma == "1. [Foo"
    assert a1.commentary == "some commentary"
    assert a2.line == 2
    assert a2.lemma == "2. [Bar"
    assert a2.commentary == "more"


def test_consolidate_continuation_merges_into_previous_annotation():
    chunk1 = Chunk(act="1", scene="4", page_number=259,
                   content="<P>56. [an Arme-gaunt Steede] Mr Warburton here seems to have stolen")
    chunk2 = Chunk(act="1", scene="4", page_number=260,
                   content="\n<C>[56. an Arme-gaunt Steede]</C>\n<P>synonymous. Spenser makes.")

    consolidator = ChunkConsolidator([chunk1, chunk2])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 1
    assert (
        consolidator.annotations[0].commentary
        == "Mr Warburton here seems to have stolen synonymous. Spenser makes."
    )


def test_consolidate_continuation_chunk_with_new_annotations_after_merge():
    # The p.259 nettles/cuckoo-flowers case: the continuation text merges
    # into the open annotation, then two new sub-annotations follow in the
    # same chunk.
    chunk1 = Chunk(act="1", scene="4", page_number=259,
                   content="<P>4. [nettles, cuckoo-flowers] commentary about early annotation")
    chunk2 = Chunk(
        act="1", scene="4", page_number=260,
        content=(
            "\n<C>[4. nettles, cuckoo-flowers]</C>\n"
            "<P>continued text about nettles."
            "<P>4. nettles] more about nettles specifically"
            "<P>4. cuckoo-flowers] more about cuckoo-flowers specifically"
        ),
    )

    consolidator = ChunkConsolidator([chunk1, chunk2])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 3
    merged, nettles, cuckoo = consolidator.annotations
    assert merged.commentary == "commentary about early annotation continued text about nettles."
    assert nettles.lemma == "4. nettles"
    assert nettles.commentary == "more about nettles specifically"
    assert cuckoo.lemma == "4. cuckoo-flowers"
    assert cuckoo.commentary == "more about cuckoo-flowers specifically"


def test_consolidate_multi_page_continuation_extends_same_annotation():
    chunk1 = Chunk(act="1", scene="4", page_number=66,
                   content="<P>91. [Enter Fool.] first part of commentary")
    chunk2 = Chunk(act="1", scene="4", page_number=67,
                   content="\n<C>[91. Enter Fool.]</C>\n<P>second part continues.")
    chunk3 = Chunk(act="1", scene="4", page_number=68,
                   content="\n<C>[91. Enter Fool.]</C>\n<P>third part concludes.")

    consolidator = ChunkConsolidator([chunk1, chunk2, chunk3])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 1
    assert consolidator.annotations[0].commentary == (
        "first part of commentary second part continues. third part concludes."
    )


def test_consolidate_chunk_with_no_act_scene():
    chunk = Chunk(act=None, scene=None, page_number=None,
                  content="<P>1. [Foo] intro commentary")
    consolidator = ChunkConsolidator([chunk])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 1
    assert consolidator.annotations[0].act is None
    assert consolidator.annotations[0].scene is None
    assert consolidator.annotations[0].lemma == "1. [Foo"


def test_consolidate_continuation_with_no_open_annotation_falls_through(caplog):
    chunk = Chunk(act=None, scene=None, page_number=None,
                  content="\n<C>[1. Foo]</C>\n<P>orphan continuation text.")
    consolidator = ChunkConsolidator([chunk])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 1
    assert consolidator.annotations[0].lemma == ""
    assert consolidator.annotations[0].commentary == "orphan continuation text."


# --- silent (unmarked) page-turn continuations ---

def test_consolidate_silent_continuation_merges_into_previous_annotation():
    # The Albany/denomination case from shake.var.lear.txt: no <C> marker,
    # the continuation prose simply resumes at the top of the next chunk.
    chunk1 = Chunk(act="1", scene="1", page_number=3,
                   content="<P>2. <B>Albany]</B> Wright: Holinshed gives the fol-")
    chunk2 = Chunk(act="1", scene="1", page_number=4,
                   content="lowing account of the origin of this name.")

    consolidator = ChunkConsolidator([chunk1, chunk2])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 1
    assert consolidator.annotations[0].lemma == "2. <B>Albany</B>"
    assert consolidator.annotations[0].commentary == (
        "Wright: Holinshed gives the fol- lowing account of the origin of this name."
    )


def test_consolidate_silent_continuation_with_new_annotations_after_merge():
    # Mirrors the <C>-marked nettles/cuckoo-flowers case: the leading prose
    # continues the open annotation, then new lemmas follow in the same chunk.
    chunk1 = Chunk(act="1", scene="4", page_number=259,
                   content="<P>4. [nettles, cuckoo-flowers] commentary about early annotation")
    chunk2 = Chunk(
        act="1", scene="4", page_number=260,
        content=(
            "continued text about nettles."
            "<P>4. nettles] more about nettles specifically"
            "<P>4. cuckoo-flowers] more about cuckoo-flowers specifically"
        ),
    )

    consolidator = ChunkConsolidator([chunk1, chunk2])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 3
    merged, nettles, cuckoo = consolidator.annotations
    assert merged.commentary == "commentary about early annotation continued text about nettles."
    assert nettles.lemma == "4. nettles"
    assert nettles.commentary == "more about nettles specifically"
    assert cuckoo.lemma == "4. cuckoo-flowers"
    assert cuckoo.commentary == "more about cuckoo-flowers specifically"


def test_consolidate_front_matter_chunk_not_treated_as_silent_continuation():
    # act/scene both None (pre-Act-1 essay material) must never be merged
    # into a preceding annotation, even if its content has no recognizable lemma.
    chunk1 = Chunk(act="1", scene="1", page_number=1,
                   content="<P>1. [Foo] some commentary")
    chunk2 = Chunk(act=None, scene=None, page_number=2,
                   content="unrelated front-matter prose with no lemma marker at all")

    consolidator = ChunkConsolidator([chunk1, chunk2])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 2
    assert consolidator.annotations[0].lemma == "1. [Foo"
    assert consolidator.annotations[1].lemma == ""
    assert consolidator.annotations[1].commentary == (
        "unrelated front-matter prose with no lemma marker at all"
    )


def test_consolidate_comma_list_lemma_not_treated_as_silent_continuation():
    # "5, 6. ..." is a real (if currently unparsed) lemma format, not
    # continuation prose -- must not be merged into the preceding annotation.
    chunk1 = Chunk(act="1", scene="1", page_number=1,
                   content="<P>1. [Foo] some commentary")
    chunk2 = Chunk(act="1", scene="1", page_number=2,
                   content="5, 6. <B>Some Phrase</B>] commentary on a line-list lemma")

    consolidator = ChunkConsolidator([chunk1, chunk2])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 2
    assert consolidator.annotations[0].lemma == "1. [Foo"
    assert consolidator.annotations[0].commentary == "some commentary"
    assert consolidator.annotations[1].lemma == ""


def test_consolidate_silent_continuation_with_no_open_annotation_unaffected():
    # No previous annotation to attach to -- must not attempt to treat this
    # as a silent continuation; falls through to normal processing.
    chunk = Chunk(act="1", scene="1", page_number=1,
                  content="orphan prose with no lemma marker and no predecessor")
    consolidator = ChunkConsolidator([chunk])
    consolidator.consolidate()

    assert len(consolidator.annotations) == 1
    assert consolidator.annotations[0].lemma == ""
    assert consolidator.annotations[0].commentary == (
        "orphan prose with no lemma marker and no predecessor"
    )


def test_serialize_round_trips_through_load_annotations(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<CC><P>1. [Foo] some commentary</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    consolidator = ChunkConsolidator(parser.chunks)
    consolidator.consolidate()

    out = io.StringIO()
    consolidator.serialize(out)
    out.seek(0)

    annotations = load_annotations(out)
    assert len(annotations) == 1
    a = annotations[0]
    assert a.act == 1
    assert a.scene == 1
    assert a.line == 1
    assert a.lemma == "1. [Foo"
    assert "some commentary" in a.commentary


def test_serialize_lifts_inline_tags_into_hi_elements(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<CC><P>1-6. <SC>Walker</SC> (<I>Crit.</I> i, 13) would read these</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    consolidator = ChunkConsolidator(parser.chunks)
    consolidator.consolidate()

    out = io.StringIO()
    consolidator.serialize(out)
    written = out.getvalue()

    assert "&lt;SC&gt;" not in written
    root = etree.fromstring(written.encode("utf-8"))
    hi_elements = root.findall(".//commentary/hi")
    assert any(h.get("rend") == "smallcaps" and h.text == "Walker" for h in hi_elements)

    out.seek(0)
    annotations = load_annotations(out)
    assert len(annotations) == 1
    assert "Walker" in annotations[0].commentary
    assert "would read these" in annotations[0].commentary
