import sys

from hypervariorum.nvs.parsing import parse_annotations_to_xml

if __name__ == "__main__":
    parse_annotations_to_xml(sys.stdin, sys.stdout)
