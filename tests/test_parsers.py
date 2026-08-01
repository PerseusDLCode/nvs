from hypervariorum.nvs.parsers import RawtoChunks


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
    assert "<P>1. some commentary\nthat continues on the next line." in parser.chunks[0]
    assert "</CC>" not in parser.chunks[0]


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
    assert "101." in parser.chunks[0]
    assert "second annotation" not in parser.chunks[0]
    assert "second annotation" in parser.chunks[1]


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
    assert "stray running text" not in parser.chunks[0]
    assert "<PB" not in parser.chunks[0]


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
    assert "inside markers" in parser.chunks[0]


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


def test_parse_carries_page_act_scene_onto_chunk_open_tag(tmp_path):
    src = (
        "<!-- START -->\n"
        "<HE>4 <I>KING LEAR</I> [<SC>act i, sc.</SC> i.</HE>\n"
        "<CC><P>1. commentary.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert "page_number='4'" in parser.chunks[0]
    assert "act='1'" in parser.chunks[0]
    assert "scene='1'" in parser.chunks[0]


def test_parse_chunk_before_any_header_omits_attributes(tmp_path):
    src = (
        "<!-- START -->\n"
        "<CC><P>1. commentary with no preceding header.</CC>\n"
        "<!-- STOP -->\n"
    )
    parser = RawtoChunks(_write(tmp_path, src))
    parser.parse()

    assert parser.chunks[0].startswith("<chunk>")


def test_serialize_writes_chunks_wrapped_in_root_element(tmp_path):
    parser = RawtoChunks(tmp_path / "unused.txt")
    parser.chunks = ["<chunk page_number='4'>first</chunk>", "<chunk page_number='5'>second</chunk>"]

    out_path = tmp_path / "out.xml"
    parser.serialize(out_path)

    written = out_path.read_text()
    assert written.startswith("<chunks>\n")
    assert written.rstrip().endswith("</chunks>")
    assert "<chunk page_number='4'>first</chunk>" in written
    assert "<chunk page_number='5'>second</chunk>" in written
