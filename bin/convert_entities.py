import sys

from hypervariorum.nvs.entities import process_line

if __name__ == "__main__":
    for line in sys.stdin:
        sys.stdout.write(f"{process_line(line)}\n")
