from pathlib import Path
import re

head_recto = r"^<HE>([0-9]+)\s+<I>.*?</I>\s+\[(.*?)</HE>"
head_verso = r"^<HE>(<SC>.*?</SC>.*?)\]\s+<I>.*?</I>\s+(\d+).*$"

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



class Parser:
    def __init__(self, file_path:Path) -> None:
        self.file_path:Path = file_path
        self.curr_act : int | None = None
        self.curr_scene: int | None = None
        self.curr_page: int | None = None
        self.chunks: list[str] = []

    def parse(self) -> None:
        start_marker = "<!-- START -->"
        stop_marker = "<!-- STOP -->"
        self.chunks = []
        with self.file_path.open() as file:
            
            in_processing:bool = False
            header = {}
            for line in file:
                stripped_line = line.strip()

                if stripped_line == start_marker:
                    in_processing = True
                    continue

                if stripped_line == stop_marker:
                    in_processing = False
                    break
                
                if in_processing is True:
                    print("in_processing")
                    if line.startswith("<HE>"):
                        header: dict = self.parse_head(line.strip())
                    if line.startswith("<CC>"):
                        current_chunk = [line[4:]]  # Keep the starting line after the <CC>

                        for inner_line in file:
                            if inner_line.rstrip().endswith("</CC>"):
                                clean_line = inner_line.replace("</CC>", "")
                                current_chunk.append(clean_line)
                                break

                            current_chunk.append(inner_line)

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
                        content = "".join(current_chunk)
                        chunk = open_tag + content + close_tag

                        # Save the clean chunk
                        self.chunks.append(chunk)
                    
    def parse_head(self, head_str) -> dict:
            """Parses a running head and returns its components."""

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
                print(f"string is not a properly formed running head: {head_str}")

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
                    
    
            

            

    
