import sys
from pathlib import Path

from hypervariorum.nvs.parsers import ChunkConsolidator, RawtoChunks

if __name__ == "__main__":
    path = Path(sys.argv[1])
    if "<!-- START -->" not in path.read_text():
        sys.exit(
            f"{path}: no <!-- START --> marker found. Add <!-- START -->/"
            "<!-- STOP --> markers to the raw file before running this pipeline."
        )

    parser = RawtoChunks(path)
    parser.parse()

    consolidator = ChunkConsolidator(parser.chunks)
    consolidator.consolidate()
    consolidator.serialize(sys.stdout)
