import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path

from lxml import etree

from hypervariorum.model.annotation import Annotation

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



@dataclass
class Chunk:
    act: str | None
    scene: str | None
    page_number: int | None
    content: str


class RawtoChunks:
    """Parses a raw file (to which start/stop markers have been added) into CC chunks."""
    def __init__(self, file_path:Path) -> None:
        self.file_path:Path = file_path
        self.chunks: list[Chunk] = []

    def parse(self) -> None:
        start_marker = "<!-- START -->"
        stop_marker = "<!-- STOP -->"
        self.chunks = []

        content = self.file_path.read_text()

        start_index = content.find(start_marker)
        if start_index == -1:
            return
        region_start = start_index + len(start_marker)

        stop_index = content.find(stop_marker, region_start)
        region_end = stop_index if stop_index != -1 else len(content)

        region = content[region_start:region_end]

        header: dict = {}
        for match in re.finditer(r"<HE>.*?</HE>|<CC>.*?</CC>", region, re.DOTALL):
            text = match.group(0)

            if text.startswith("<HE>"):
                header = self.parse_head(text)
                continue

            # Construct the chunk
            content_inner = text[len("<CC>"):-len("</CC>")]
            chunk = Chunk(
                act=header.get('act'),
                scene=header.get('scene'),
                page_number=header.get('page_number'),
                content=content_inner,
            )

            # Save the clean chunk
            self.chunks.append(chunk)

    def serialize(self, out_path: Path) -> None:
        """Writes self.chunks to out_path, wrapped in a <chunks> root element."""
        with out_path.open("w") as file:
            file.write("<chunks>\n")
            for chunk in self.chunks:
                open_tag:str = "<chunk"
                if chunk.page_number is not None:
                    open_tag = open_tag + f" page_number='{chunk.page_number}'"
                if chunk.act is not None:
                    open_tag = open_tag + f" act='{chunk.act}'"
                if chunk.scene is not None:
                    open_tag = open_tag + f" scene='{chunk.scene}'"
                open_tag = open_tag + ">"
                file.write(open_tag + chunk.content + "</chunk>")
                file.write("\n")
            file.write("</chunks>\n")

    def parse_head(self, head_str) -> dict:
            """Parses a running head and returns its components."""

            
            head_recto = r"^<HE>([0-9]+)\s+<I>.*?</I>\s+\[(.*?)</HE>"
            head_verso = r"^<HE>(<SC>.*?</SC>.*?)\]\s+<I>.*?</I>\s+(\d+).*$"

            result = {}
            act_scene = None

            # First see if it is a recto header
            if match := re.search(head_recto, head_str):
                result['page_number'] = int(match.group(1))
                act_scene  = match.group(2)

            elif match := re.search(head_verso, head_str):
                result['page_number'] = int(match.group(2))
                act_scene: str | None = match.group(1)
            else:
                logging.warning(f"string is not a properly formed running head: {head_str}")

            # parse the act_scene string
            # first get rid of the <SC> tags
            if act_scene is not None:
                string = re.sub(r"</?SC>","", act_scene)
                # now extract the numbers
                pattern = r"^act\s+(.*?), sc\.\s+(.*?)\.$"
                match = re.search(pattern, string)
                if match is not None:
                    result['act'] = roman_to_int(match.group(1))
                    result['scene'] = roman_to_int(match.group(2))
            return result
                    
def split_annotation_chunks(cc_inner: str) -> list[str]:
    """Splits the inner content of a <CC> block on <P>-boundaries that start a new annotation."""
    return re.split(r"<P>(?=\d+(?:[-–]\d+)?\.?|<B>.*?\])", cc_inner)


def _normalize_bracket_lemma(raw_lemma: str) -> str:
    """Applies the `]</B>`/`</B>]` swap and trailing-`]` strip shared by bracketed lemmas."""
    lemma = raw_lemma.strip().replace("]</B>", "</B>").replace("</B>]", "</B>")
    if lemma.endswith("]"):
        lemma = lemma[:-1].strip()
    return lemma


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
        lemma = _normalize_bracket_lemma(part1 + part2)
        commentary = chunk[len(pattern_a.group(0)):].strip()
    elif pattern_b:
        lemma = _normalize_bracket_lemma(pattern_b.group(1))
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


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value is not None else None


_CONTINUATION_LINE_RE = re.compile(r"^\s*<C>.*?</C>\s*$", re.MULTILINE)


class ChunkConsolidator:
    """Consolidates a list of Chunks into a list of Annotations."""
    def __init__(self, chunk_list: list[Chunk]) -> None:
        self.input_list: list[Chunk] = chunk_list
        self.annotations: list[Annotation] = []

    def is_continuation(self, chunk: Chunk) -> bool:
        return _CONTINUATION_LINE_RE.search(chunk.content) is not None

    def consolidate(self) -> None:
        self.annotations = []
        for chunk in self.input_list:
            if self.is_continuation(chunk):
                self._consolidate_continuation(chunk)
            else:
                self._consolidate_parts(chunk, split_annotation_chunks(chunk.content))

    def _consolidate_continuation(self, chunk: Chunk) -> None:
        match = _CONTINUATION_LINE_RE.search(chunk.content)
        remainder = chunk.content[match.end():].lstrip()
        if remainder.startswith("<P>"):
            remainder = remainder[len("<P>"):]

        if not self.annotations:
            logging.warning("continuation marker with no open annotation: %r", chunk)
            self._consolidate_parts(chunk, split_annotation_chunks(remainder))
            return

        parts = split_annotation_chunks(remainder)
        continuation_text = parts[0].strip()
        prev = self.annotations[-1]
        self.annotations[-1] = replace(
            prev, commentary=(prev.commentary.rstrip() + " " + continuation_text).strip()
        )
        self._consolidate_parts(chunk, parts[1:])

    def _consolidate_parts(self, chunk: Chunk, parts: list[str]) -> None:
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith("<P>"):
                part = part[len("<P>"):].strip()
            lemma, commentary = parse_lemma(part)
            line_info = extract_line_info(lemma)
            self.annotations.append(Annotation(
                act=_int_or_none(chunk.act),
                scene=_int_or_none(chunk.scene),
                line=_int_or_none(line_info.get("line")),
                line_from=_int_or_none(line_info.get("line-from")),
                line_to=_int_or_none(line_info.get("line-to")),
                lemma=lemma,
                commentary=commentary,
            ))

    def serialize(self, out) -> None:
        """Writes self.annotations to out (a writable text stream) as <annotations>...</annotations> XML."""
        root = etree.Element("annotations")
        for annotation in self.annotations:
            attrib: dict[str, str] = {}
            if annotation.act is not None:
                attrib["act"] = str(annotation.act)
            if annotation.scene is not None:
                attrib["scene"] = str(annotation.scene)
            if annotation.line is not None:
                attrib["line"] = str(annotation.line)
            if annotation.line_from is not None:
                attrib["line-from"] = str(annotation.line_from)
            if annotation.line_to is not None:
                attrib["line-to"] = str(annotation.line_to)
            elem = etree.SubElement(root, "annotation", attrib=attrib)
            etree.SubElement(elem, "lemma").text = annotation.lemma
            etree.SubElement(elem, "commentary").text = annotation.commentary
        xml_bytes = etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True)
        out.write(xml_bytes.decode("utf-8"))

