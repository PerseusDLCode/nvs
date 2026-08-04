from dataclasses import dataclass
from pathlib import Path
from typing import IO
import xml.etree.ElementTree as ET


@dataclass(frozen=True, slots=True)
class Annotation:
    act: int | None
    scene: int | None
    line: int | None
    line_from: int | None
    line_to: int | None
    lemma: str
    commentary: str

    @property
    def is_range(self) -> bool:
        return self.line_from is not None and self.line_to is not None


def load_annotations(source: str | Path | IO[str]) -> list[Annotation]:
    root = ET.parse(source).getroot()
    return [_annotation_from_element(elem) for elem in root.findall("annotation")]


def _text_content(elem: ET.Element, tag: str) -> str:
    child = elem.find(tag)
    return "".join(child.itertext()) if child is not None else ""


def _annotation_from_element(elem: ET.Element) -> Annotation:
    def _int_or_none(name: str) -> int | None:
        v = elem.get(name)
        return int(v) if v is not None else None

    commentary_raw = _text_content(elem, "commentary")
    commentary = "\n".join(
        line.strip() for line in commentary_raw.strip("\n").splitlines()
    ).strip()

    return Annotation(
        act=_int_or_none("act"),
        scene=_int_or_none("scene"),
        line=_int_or_none("line"),
        line_from=_int_or_none("line-from"),
        line_to=_int_or_none("line-to"),
        lemma=_text_content(elem, "lemma").strip(),
        commentary=commentary,
    )
