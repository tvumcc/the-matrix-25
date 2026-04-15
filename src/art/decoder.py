"""decoder for encoded.dat

mirrors the basic decoding process done by the chip.

get_all() returns a dictionary of animations, keyed by name for use in the simulator.
"""

import re
import sys
from pathlib import Path

from ansi import bits, error, heading, key

DATA_FILE = Path(__file__).resolve().with_name("encoded.dat")


def get_all() -> dict[str, list[tuple[int, list[list[int]]]]]:
    """decode every animation from encoded.dat."""
    text = DATA_FILE.read_text()
    arrays = re.findall(r"\{([^}]*)\}", text, flags=re.DOTALL)
    if len(arrays) < 3:
        raise ValueError("encoded.dat is missing required arrays")

    # parse arrays from strings (from encoded.dat)
    # in the chip, these would be written in source code
    basis = [int(t.strip(), 0) for t in arrays[0].split(",") if t.strip()]
    starts = [int(t.strip(), 0) for t in arrays[1].split(",") if t.strip()]
    frames = [int(t.strip(), 0) for t in arrays[2].split(",") if t.strip()]

    # decode frames into animations
    result: dict[str, list[tuple[int, list[list[int]]]]] = {}

    for i, start in enumerate(starts):
        # get the end index for the current animation
        end = starts[i + 1] if i + 1 < len(starts) else len(frames)

        # decode each frame into a delay and grid
        anim: list[tuple[int, list[list[int]]]] = []

        for packed in frames[start:end]:
            # decode the delay from the flags
            delay = sum(
                basis[b] for b in range(min(7, len(basis))) if (packed >> (31 - b)) & 1
            )

            # decode the grid from the packed value
            grid = [
                [(packed >> (24 - r * 5 - c)) & 1 for c in range(5)] for r in range(5)
            ]
            anim.append((delay, grid))
        result[f"anim_{i:02d}"] = anim

    return result


def main() -> None:
    if len(sys.argv) < 2:
        all_anims = get_all()
        print(error("usage: python decoder.py <index>"))
        print(f"{heading('available')}: {', '.join(all_anims.keys())}")
        sys.exit(1)

    idx = int(sys.argv[1])
    all_anims = get_all()
    name = f"anim_{idx:02d}"
    if name not in all_anims:
        print(error(f"index {idx} out of range (0..{len(all_anims) - 1})"))
        sys.exit(1)

    anim = all_anims[name]
    print(f"{heading('frames')}: {len(anim)}\n")
    for i, (delay, grid) in enumerate(anim):
        parts = [bits("".join(str(c) for c in row)) for row in grid]
        print(f"  {key(f'{i:3d}')}  {delay:4d}ms  {'  '.join(parts)}")


if __name__ == "__main__":
    main()
