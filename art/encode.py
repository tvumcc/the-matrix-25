"""converts animations to code for the LED matrix.

the encoding packs timing into the spare 3 bits of each row's uint8_t:
  uint8_t row = (basis_index << 5) | led_bits
  frame_delay_ms = sum of basis[row_i >> 5] for each of the 5 rows

this means every timing must be expressible as a sum of exactly 5
basis lookups (with basis[0]=0 acting as a no-op).
"""

import os
from math import gcd
from functools import reduce

from ansi import accent, alert, error, heading, info, key, muted, success, warning
import cleaner
from interpret import parse_text as parse_animation

NUM_ROWS = 5
MAX_BASIS_SIZE = 7  # 7 bits -> basis flags
ANIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animations")

# TODO: animations need to be excluded to fit in memory
EXCLUDED_ANIMATIONS = []

# exclusion round 1
EXCLUDED_ANIMATIONS += [
    "arrows",
    "cascade",
    "cross",
    "checkerboard",
    "loading",
    "spotlight",
    "starburst",
    "strobe",
    "glitch",
]

# exclusion round 2
EXCLUDED_ANIMATIONS += ["bounce", "orbit", "scan", "wipe", "snake"]

# exclusion round 3
EXCLUDED_ANIMATIONS += ["basic","breathe","matrix"]

# round 4
EXCLUDED_ANIMATIONS += ["conway", "drop", "spiral"]

# need to cut matrix or rain


def collect_animations(
    excluded_names: list[str] | None = None,
) -> tuple[dict[str, list[tuple[int, list[list[int]]]]], list[str], list[str]]:
    animations: dict[str, list[tuple[int, list[list[int]]]]] = {}
    excluded = set(excluded_names or [])
    excluded_found: list[str] = []
    for file in sorted(os.listdir(ANIM_DIR)):
        if file.endswith(".anim"):
            name = file.removesuffix(".anim")
            if name in excluded:
                excluded_found.append(name)
                continue
            with open(os.path.join(ANIM_DIR, file)) as f:
                animations[name] = parse_animation(f.read())
    excluded_missing = sorted(excluded - set(excluded_found))
    return animations, sorted(excluded_found), excluded_missing


def unique_timings(
    animations: dict[str, list[tuple[int, list[list[int]]]]],
) -> set[int]:
    return {timing for anim in animations.values() for timing, _ in anim}


def reachable_sums(basis: list[int], picks: int, max_val: int) -> set[int]:
    """all values expressible as a sum of exactly `picks` values from basis.
    since 0 is in basis, this is equivalent to sums of *at most* `picks` nonzero values.
    """
    current = {0}
    for _ in range(picks):
        nxt: set[int] = set()
        for v in current:
            for b in basis:
                s = v + b
                if s <= max_val:
                    nxt.add(s)
        current = nxt
    return current


def find_basis(
    targets: set[int], max_size: int = MAX_BASIS_SIZE, picks: int = NUM_ROWS
) -> list[int]:
    """find a basis of at most `max_size` values (including 0) such that
    every target is a sum of exactly `picks` basis values.

    uses GCD to shrink the search space, then scales back.
    uses greedy search: each round, add the candidate that covers the most
    uncovered targets. falls back to backtracking if greedy gets stuck.
    """
    g = reduce(gcd, targets)
    scaled = {t // g for t in targets}
    max_t = max(scaled)

    basis = [0]
    uncovered = scaled.copy()

    while uncovered and len(basis) < max_size:
        best_val = -1
        best_count = 0

        for candidate in range(1, max_t + 1):
            if candidate in basis:
                continue
            trial = basis + [candidate]
            reach = reachable_sums(trial, picks, max_t)
            covered = len(uncovered & reach)
            if covered > best_count:
                best_count = covered
                best_val = candidate

        if best_val == -1:
            break

        basis.append(best_val)
        uncovered -= reachable_sums(basis, picks, max_t)

    return sorted(b * g for b in basis)


def decompose(target: int, basis: list[int], picks: int = NUM_ROWS) -> list[int] | None:
    """find indices into basis that sum to target using exactly `picks` values.
    returns list of `picks` indices, or None if impossible.
    """

    def backtrack(remaining: int, depth: int, path: list[int]) -> list[int] | None:
        if depth == picks:
            return path[:] if remaining == 0 else None
        for i, b in enumerate(basis):
            if b > remaining:
                break
            path.append(i)
            result = backtrack(remaining - b, depth + 1, path)
            if result is not None:
                return result
            path.pop()
        return None

    return backtrack(target, 0, [])


def main() -> None:
    excluded_names: list[str] = list(set(EXCLUDED_ANIMATIONS))
    animations, excluded_found, excluded_missing = collect_animations(excluded_names)
    animations, clean_stats = cleaner.clean_all(animations)
    timings = unique_timings(animations)

    print(
        f"{key('animations')}: {len(animations)}, "
        f"{key('excluded')}: {len(excluded_found)}, "
        f"{key('unique timings')}: {len(timings)}"
    )
    if excluded_names:
        print(f"{key('excluded list')}: {sorted(excluded_names)}")
    if excluded_found:
        print(f"{warning('excluded now')}: {excluded_found}")
    if excluded_missing:
        print(f"{warning('missing excludes')}: {excluded_missing}")
    print(f"{key('timings')}: {sorted(timings)}\n")
    if not animations:
        print(error("no animations selected after exclusions"))
        return

    if clean_stats:
        print(f"{heading('cleaned before encoding')}: {len(clean_stats)}")
        for item in clean_stats:
            print(
                f"  {success(str(item['name']))}: {item['before']} -> {item['after']} "
                f"(trimmed {item['trimmed']}, bytes saved {item['bytes_saved']})"
            )
        print()

    g = reduce(gcd, timings)
    print(f"{key('GCD')}: {g}ms")

    basis = find_basis(timings)
    print(f"{heading(f'basis ({len(basis)} slots)')}: {basis}")

    # ensure every timing can be represented.
    reach = reachable_sums(basis, NUM_ROWS, max(timings))
    missing = timings - reach
    if missing:
        print(
            f"\n{error('FAILED')} {warning('unreachable timings')}: {sorted(missing)}"
        )
        return

    print(f"\n{success(f'all {len(timings)} timings are reachable')}\n")

    # flatten all animations into one row stream.
    # ranges in this stream are stored as [start, end).
    everything: list[str] = []
    anim_ranges: dict[str, tuple[int, int]] = {}

    keys = sorted(animations.keys())
    for name in keys:
        animation = animations[name]
        starting_index = len(everything)
        for frame_idx, frame in enumerate(animation):
            # encode delay by packing the timing basis index into top 7 bits.
            indices = decompose(frame[0], basis)
            if indices is None:
                raise ValueError(
                    f"failed to decompose timing of {name} frame {frame_idx}: {frame[0]}"
                )

            basis_flags = [False] * 7
            for idx in indices:
                basis_flags[idx] = True
            flags_str = "".join("1" if b else "0" for b in basis_flags)

            grid_str = ""
            for row_val in frame[1]:
                grid_str += "".join(str(i) for i in row_val)

            combined = flags_str + grid_str
            everything.append(combined)
        ending_index = len(everything)
        anim_ranges[name] = (starting_index, ending_index)

    start_indices = [anim_ranges[name][0] for name in keys]

    total_frames = len(everything)
    animation_bytes = total_frames * 4
    index_w = len(str(total_frames))
    rows: list[dict[str, str]] = []

    for name, (start, end) in anim_ranges.items():
        frame_count = end - start
        byte_count = frame_count * 4
        percent = (
            0.0 if animation_bytes == 0 else (byte_count / animation_bytes) * 100.0
        )
        range_text = f"[{start:>{index_w}}, {end:>{index_w}})"
        rows.append(
            {
                "name": name,
                "range": range_text,
                "frames": str(frame_count),
                "bytes": str(byte_count),
                "percent": f"{percent:6.2f}%",
            }
        )

    name_w = max(len("name"), *(len(r["name"]) for r in rows))
    range_w = max(len("range"), *(len(r["range"]) for r in rows))
    frames_w = max(len("frames"), *(len(r["frames"]) for r in rows))
    bytes_w = max(len("bytes"), *(len(r["bytes"]) for r in rows))
    percent_w = max(len("% bytes"), *(len(r["percent"]) for r in rows))

    def _left_cell(value: str, width: int, colorize) -> str:
        pad_len = max(0, width - len(value))
        return (
            colorize(value) + muted("." * min(pad_len, 6)) + (" " * max(0, pad_len - 6))
        )

    def _right_cell(value: str, width: int, colorize) -> str:
        pad_len = max(0, width - len(value))
        return (
            (" " * max(0, pad_len - 6)) + muted("." * min(pad_len, 6)) + colorize(value)
        )

    header_cells = [
        info(f"{'name':<{name_w}}"),
        accent(f"{'range':<{range_w}}"),
        key(f"{'frames':>{frames_w}}"),
        warning(f"{'bytes':>{bytes_w}}"),
        alert(f"{'% bytes':>{percent_w}}"),
    ]
    header = "  " + "  ".join(header_cells)
    print(header)
    print(muted("  " + "-" * (name_w + range_w + frames_w + bytes_w + percent_w + 8)))

    for row in rows:
        name_cell = _left_cell(row["name"], name_w, info)
        range_cell = _left_cell(row["range"], range_w, accent)
        frames_cell = _right_cell(row["frames"], frames_w, key)
        bytes_cell = _right_cell(row["bytes"], bytes_w, warning)
        percent_cell = _right_cell(row["percent"], percent_w, alert)
        print(
            f"  {name_cell}  {range_cell}  {frames_cell}  {bytes_cell}  {percent_cell}"
        )

    # write packed payload to disk.
    with open("encoded.dat", "w") as f:
        # write basis values.
        f.write("# basis: \n")
        f.write("{")
        f.write(",".join(str(b) for b in basis))
        f.write("}\n")

        # write start indices.
        f.write("\n# start_indices: \n")
        f.write("{")
        f.write(",".join(str(i) for i in start_indices))
        f.write("}\n")

        # write all packed rows.
        f.write("\n# everything: \n")
        f.write("{")
        f.write(",".join(["0b" + e for e in everything]))
        f.write("}\n")
        f.write("\n# everything_hex: \n")
        f.write("{")
        f.write(",".join(["0x" + hex(int(e, 2))[2:] for e in everything]))
        f.write("}\n")
        f.write("\n# everything_int: \n")
        f.write("{")
        f.write(",".join([str(int(e, 2)) for e in everything]))
        f.write("}\n")

    print(success("\nall data written to encoded.dat\n"))

    anim_bytes = len(everything) * 4
    start_indices_bytes = len(anim_ranges)
    basis_bytes = len(basis)
    total_bytes = anim_bytes + start_indices_bytes + basis_bytes

    print(heading("Memory Footprint:"))
    print(
        f"  {key('Animation Data (32-bit frames)')}: {anim_bytes} bytes ({total_frames} frames)"
    )
    print(
        f"  {key('Start Indices (8-bit)')}:          {start_indices_bytes} bytes ({len(anim_ranges)} animations)"
    )
    print(f"  {key('Basis Array (8-bit)')}:            {basis_bytes} bytes")
    print(f"  {muted('-' * 45)}")
    print(f"  {warning('Total Required Memory')}:          {total_bytes} bytes")


if __name__ == "__main__":
    main()
