from hypervariorum.nvs.entities import convert_entities, process_line


def test_convert_entities_accents():
    assert convert_entities("caf&eacute;") == "café"
    assert convert_entities("&Agrave; bient&ocirc;t") == "À bientôt"


def test_convert_entities_punctuation():
    assert convert_entities("a&mdash;b") == "a—b"
    assert convert_entities("&ldquo;quoted&rdquo;") == "“quoted”"


def test_convert_entities_nbsp_becomes_space():
    assert convert_entities("a&nbsp;b") == "a b"


def test_process_line_strips_and_converts():
    assert process_line("  caf&eacute;  \n") == "café"


def test_convert_entities_numeric_codes():
    assert convert_entities("<01>e wandryng") == "þe wandryng"
    assert convert_entities("<03>10") == "£10"


def test_convert_entities_illegible_marker():
    assert convert_entities("H<*> childed") == "H<unclear/> childed"
