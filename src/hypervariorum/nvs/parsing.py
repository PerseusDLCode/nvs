import re

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

def parse_annotations_to_xml(in_file, out):
    content = in_file.read()

    # Track active context
    current_act = None
    current_scene = None

    # We will look for <HE> tags and <CC> blocks in order of appearance
    # Using re.finditer allows us to process the file linearly
    elements = re.finditer(r"(<HE>.*?</HE>|<CC>.*?</CC>)", content, re.DOTALL)

    out.write('<?xml version="1.0" encoding="utf-8"?>\n')
    out.write('<annotations>\n')

    for elem in elements:
        text = elem.group(1)

        # --- 1. UPDATE RUNNING HEAD CONTEXT ---
        if text.startswith("<HE>"):
            # Clean tag and search for act and scene markers (e.g., act i, sc. i)
            he_content = re.sub(r"<[^>]+>", "", text).lower()
            match = re.search(r"act\s+([ivxl]+),\s*sc\.\s*([ivxl\d]+)", he_content)
            if match:
                current_act = roman_to_int(match.group(1))
                current_scene = roman_to_int(match.group(2))
            continue

        # --- 2. PROCESS COMMENTARY BLOCK (<CC>) ---
        # Strip outer <CC> tags
        cc_inner = text[4:-5].strip()

        # Split into individual annotation chunks on internal <P> boundaries
        annotation_chunks = re.split(r"<P>(?=\d+(?:[-–]\d+)?\.?|<B>.*?\])", cc_inner)

        for chunk in annotation_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            if chunk.startswith("<P>"):
                chunk = chunk[3:].strip()

            # --- LEMMA PARSING ---
            lemma = ""
            commentary = chunk

            # Match Patterns
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

            # --- EXTRACT LINE DETAILS FROM LEMMA ---
            line_attr = ""
            if lemma:
                # Look for ranges (e.g., "1-6.") or single lines (e.g., "2.")
                range_match = re.match(r"^(\d+)[-–](\d+)\.", lemma)
                single_match = re.match(r"^(\d+)\.", lemma)

                if range_match:
                    line_attr = f' line-from="{range_match.group(1)}" line-to="{range_match.group(2)}"'
                elif single_match:
                    line_attr = f' line="{single_match.group(1)}"'

            # Add structural act and scene contexts if found
            act_attr = f' act="{current_act}"' if current_act else ''
            scene_attr = f' scene="{current_scene}"' if current_scene else ''

            # --- OUTPUT GENERATION ---
            out.write(f"  <annotation{act_attr}{scene_attr}{line_attr}>\n")
            out.write(f"    <lemma>{lemma}</lemma>\n")
            out.write("    <commentary>\n")

            for line in commentary.splitlines():
                out.write(f"      {line}\n")

            out.write("    </commentary>\n")
            out.write("  </annotation>\n\n")

    out.write('</annotations>\n')
