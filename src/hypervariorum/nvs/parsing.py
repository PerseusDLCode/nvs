import re
from collections.abc import Iterator

from lxml import etree


def roman_to_int(roman_str):
    """Converts a small Roman numeral string (like i, ii, iii, iv) to an integer string."""
    roman_str = roman_str.upper().strip()
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
    total = 0
    prev_value = 0
    for char in reversed(roman_str):
        value = roman_map.get(char, 0)
        if value >= prev_value:
            total += value
        else:
            total -= value
        prev_value = value
    return str(total) if total > 0 else None


def extract_elements(content: str) -> Iterator[str]:
    """Yields <HE>...</HE> and <CC>...</CC> blocks in order of appearance."""
    for match in re.finditer(r"(<HE>.*?</HE>|<CC>.*?</CC>)", content, re.DOTALL):
        yield match.group(1)


def parse_running_head(text: str) -> tuple[str | None, str | None] | None:
    """Extracts act/scene from an <HE> block, e.g. "act i, sc. ii".

    Returns None if no act/scene marker is found, so the caller can leave
    the current act/scene context unchanged.
    """
    he_content = re.sub(r"<[^>]+>", "", text).lower()
    match = re.search(r"act\s+([ivxl]+),\s*sc\.\s*([ivxl\d]+)", he_content)
    if not match:
        return None
    return roman_to_int(match.group(1)), roman_to_int(match.group(2))


def split_annotation_chunks(cc_inner: str) -> list[str]:
    """Splits the inner content of a <CC> block on <P>-boundaries that start a new annotation."""
    return re.split(r"<P>(?=\d+(?:[-–]\d+)?\.?|<B>.*?\])", cc_inner)


def parse_lemma(chunk: str) -> tuple[str, str]:
    """Splits an annotation chunk into (lemma, commentary) using a 3-pattern fallback."""
    lemma = ""
    commentary = chunk

    pattern_c = re.match(r"^(\d+(?:[-–]\d+)?\.)\s+", chunk)
    pattern_a = re.match(r"^(\d+(?:[-–]\d+)?\.\s*)(<B>.*?\](?:</B>)?|[^<\n]*?\])", chunk, re.DOTALL)
    pattern_b = re.match(r"^(<B>.*?\](?:</B>)?|[^<\n]*?\])", chunk, re.DOTALL)

    if pattern_a:
        part1 = pattern_a.group(1) or ""
        part2 = pattern_a.group(2) or ""
        raw_lemma = (part1 + part2).strip()
        lemma = raw_lemma.replace("]</B>", "</B>").replace("</B>]", "</B>")
        if lemma.endswith("]"):
            lemma = lemma[:-1].strip()
        commentary = chunk[len(pattern_a.group(0)):].strip()
    elif pattern_b:
        raw_lemma = pattern_b.group(1).strip()
        lemma = raw_lemma.replace("]</B>", "</B>").replace("</B>]", "</B>")
        if lemma.endswith("]"):
            lemma = lemma[:-1].strip()
        commentary = chunk[len(pattern_b.group(0)):].strip()
    elif pattern_c:
        lemma = pattern_c.group(1).strip()
        commentary = chunk[len(pattern_c.group(1)):].strip()

    return lemma, commentary


def extract_line_info(lemma: str) -> dict[str, str]:
    """Extracts line/line-from/line-to attributes from a lemma's leading line number(s)."""
    if not lemma:
        return {}

    range_match = re.match(r"^(\d+)[-–](\d+)\.", lemma)
    if range_match:
        return {"line-from": range_match.group(1), "line-to": range_match.group(2)}

    single_match = re.match(r"^(\d+)\.", lemma)
    if single_match:
        return {"line": single_match.group(1)}

    return {}


def build_annotation_element(
    lemma: str,
    commentary: str,
    act: str | None,
    scene: str | None,
    line_info: dict[str, str],
) -> etree._Element:
    attrib: dict[str, str] = {}
    if act:
        attrib["act"] = act
    if scene:
        attrib["scene"] = scene
    attrib.update(line_info)

    annotation = etree.Element("annotation", attrib=attrib)
    etree.SubElement(annotation, "lemma").text = lemma
    etree.SubElement(annotation, "commentary").text = commentary
    return annotation


def parse_annotations_to_xml(in_file, out) -> None:
    content = in_file.read()

    current_act: str | None = None
    current_scene: str | None = None

    root = etree.Element("annotations")

    for text in extract_elements(content):
        if text.startswith("<HE>"):
            running_head = parse_running_head(text)
            if running_head is not None:
                current_act, current_scene = running_head
            continue

        cc_inner = text[4:-5].strip()

        for chunk in split_annotation_chunks(cc_inner):
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk.startswith("<P>"):
                chunk = chunk[3:].strip()

            lemma, commentary = parse_lemma(chunk)
            line_info = extract_line_info(lemma)

            root.append(
                build_annotation_element(lemma, commentary, current_act, current_scene, line_info)
            )

    xml_bytes = etree.tostring(
        root, xml_declaration=True, encoding="utf-8", pretty_print=True
    )
    out.write(xml_bytes.decode("utf-8"))
