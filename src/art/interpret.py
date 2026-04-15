"""interpreter for .anim payload text."""

import sys

from ansi import bits, error, heading, key

ROWS = 5
COLS = 5
DEFAULT_DELAY_MS = 200


def parse_lines(lines: list[str]) -> list[tuple[int, list[list[int]]]]:
    """parse .anim lines into (delay_ms, 5x5 grid) frames."""
    default_delay = DEFAULT_DELAY_MS
    frames: list[tuple[int | None, list[list[int]]]] = []
    current_rows: list[list[int]] = []
    current_delay: int | None = None

    for raw in lines:
        line = raw.strip()

        if not line:
            if current_rows:
                frames.append((current_delay, current_rows))
                current_rows = []
                current_delay = None
            continue

        if line.startswith("#"):
            continue
        if line.startswith("delay:"):
            default_delay = int(line.split(":")[1].strip())
            continue
        if line.startswith("@"):
            current_delay = int(line[1:].strip())
            continue
        if len(line) == COLS and all(c in "01" for c in line):
            current_rows.append([int(c) for c in line])

    if current_rows:
        frames.append((current_delay, current_rows))

    return [(d if d is not None else default_delay, g) for d, g in frames]


def parse_text(text: str) -> list[tuple[int, list[list[int]]]]:
    """parse .anim text into (delay_ms, 5x5 grid) frames."""
    return parse_lines(text.splitlines())


def main() -> None:
    if sys.stdin.isatty():
        print(error("usage: cat file.anim | python interpret.py"))
        sys.exit(1)

    frames = parse_text(sys.stdin.read())
    print(f"{heading('frames')}: {len(frames)}\n")
    for i, (delay, grid) in enumerate(frames):
        rows_str = "  ".join(bits("".join(str(c) for c in row)) for row in grid)
        print(f"  {key(f'{i:3d}')}  {delay:4d}ms  {rows_str}")


if __name__ == "__main__":
    main()
