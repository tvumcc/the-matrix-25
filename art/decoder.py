"""decoder for encoded.dat animation payloads."""

import re
import sys
from pathlib import Path

from ansi import bits, error, heading, key

ROWS = 5
COLS = 5
DATA_FILE = Path(__file__).resolve().with_name("encoded.dat")


def _parse_int_array(body: str) -> list[int]:
    values: list[int] = []
    tokens = body.split(",")
    for token in tokens:
        item = token.strip()
        if not item:
            continue
        if item.startswith("0b"):
            values.append(int(item[2:], 2))
        else:
            values.append(int(item))
    return values


def _load_encoded() -> tuple[list[int], list[int], list[int]]:
    with open(DATA_FILE) as f:
        text = f.read()

    arrays = re.findall(r"\{([^}]*)\}", text, flags=re.DOTALL)
    if len(arrays) < 3:
        raise ValueError("encoded.dat is missing required arrays")

    basis = _parse_int_array(arrays[0])
    start_indices = _parse_int_array(arrays[1])
    everything = _parse_int_array(arrays[2])

    if not basis:
        raise ValueError("basis array is empty")
    if not start_indices:
        raise ValueError("start_indices array is empty")

    return basis, start_indices, everything


def _decode_span(
    basis: list[int], everything: list[int], start: int, end: int
) -> list[tuple[int, list[list[int]]]]:
    count = end - start
    if count < 0 or count % ROWS != 0:
        raise ValueError("invalid animation row span in encoded.dat")

    frames: list[tuple[int, list[list[int]]]] = []
    pos = start
    while pos < end:
        delay = 0
        grid: list[list[int]] = []

        row_offset = 0
        while row_offset < ROWS:
            packed = everything[pos + row_offset]
            basis_idx = (packed >> 5) & 0b111
            led_bits = packed & 0b11111

            if basis_idx >= len(basis):
                raise ValueError(f"basis index {basis_idx} is out of range")

            delay += basis[basis_idx]

            row: list[int] = []
            bit = COLS - 1
            while bit >= 0:
                row.append((led_bits >> bit) & 1)
                bit -= 1
            grid.append(row)
            row_offset += 1

        frames.append((delay, grid))
        pos += ROWS

    return frames


def get_all() -> dict[str, list[tuple[int, list[list[int]]]]]:
    """decode every animation as {name: Animation}."""
    basis, start_indices, everything = _load_encoded()
    result: dict[str, list[tuple[int, list[list[int]]]]] = {}

    i = 0
    while i < len(start_indices):
        name = f"anim_{i:02d}"
        start = start_indices[i]
        if i + 1 < len(start_indices):
            end = start_indices[i + 1]
        else:
            end = len(everything)
        result[name] = _decode_span(basis, everything, start, end)
        i += 1

    return result


def list_names() -> list[str]:
    """list synthetic names in encoded order."""
    return list(get_all().keys())


def _resolve_index(name: str) -> int:
    raw = name.strip()
    if raw.endswith(".anim"):
        raw = raw[:-5]
    if raw.startswith("anim_"):
        raw = raw[5:]

    if not raw.isdigit():
        raise ValueError(
            f"invalid animation id '{name}', use anim_00 style or a numeric index"
        )
    return int(raw)


def parse(name: str) -> list[tuple[int, list[list[int]]]]:
    all_anims = get_all()
    if name in all_anims:
        return all_anims[name]

    anim_index = _resolve_index(name)
    key = f"anim_{anim_index:02d}"
    if key not in all_anims:
        raise IndexError(f"animation index out of range: {anim_index}")
    return all_anims[key]


def main() -> None:
    if len(sys.argv) < 2:
        print(error("usage: python decoder.py <anim_id>"))
        print(f"{heading('available')}: {', '.join(list_names())}")
        sys.exit(1)

    frames = parse(sys.argv[1])
    print(f"{heading('frames')}: {len(frames)}\n")
    i = 0
    while i < len(frames):
        delay, grid = frames[i]
        parts: list[str] = []
        for row in grid:
            bit_str = "".join(str(c) for c in row)
            parts.append(bits(bit_str))
        print(f"  {key(f'{i:3d}')}  {delay:4d}ms  {'  '.join(parts)}")
        i += 1


if __name__ == "__main__":
    main()
