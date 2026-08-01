import logging
import re
from pathlib import Path

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



class RawtoChunks:
    """Parses a raw file (to which start/stop markers have been added) into CC chunks."""
    def __init__(self, file_path:Path) -> None:
        self.file_path:Path = file_path
        self.chunks: list[str] = []

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
            open_tag:str = "<chunk"
            if page_number := header.get('page_number', None):
                open_tag = open_tag + f" page_number='{page_number}'"
            if act := header.get('act', None):
                open_tag = open_tag + f" act='{act}'"
            if scene := header.get('scene', None):
                open_tag = open_tag + f" scene='{scene}'"
            open_tag = open_tag + ">"
            close_tag:str = "</chunk>"
            content_inner = text[len("<CC>"):-len("</CC>")]
            chunk = open_tag + content_inner + close_tag

            # Save the clean chunk
            self.chunks.append(chunk)

    def serialize(self, out_path: Path) -> None:
        """Writes self.chunks to out_path, wrapped in a <chunks> root element."""
        with out_path.open("w") as file:
            file.write("<chunks>\n")
            for chunk in self.chunks:
                file.write(chunk)
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
                    
class ChunkConsolidator:
    """Parses a chunk into annotations."""
    def __init__(self, chunk_list:list) -> None:
            self.input_list:list = chunk_list

    def is_continuation(self, chunk) -> bool:
        pass

    
