"""converts animations to code for the LED matrix.

each frame is a 32-bit value: 7 flag bits (31..25) + 25 grid bits (24..0).
each flag selects a basis value; frame delay = sum of selected basis values.
all flags off = 0ms delay, so 0 never needs to appear in the basis.
"""

import os
from math import gcd
from functools import reduce
from collections.abc import Callable

from ansi import accent, alert, error, heading, info, key, muted, success, warning
import cleaner
from interpret import parse_text as parse_animation

MAX_BASIS_SIZE = 7
ANIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animations")

# TODO: animations need to be excluded to fit in memory
EXCLUDED_ANIMATIONS = [
    "arrows",
    "cascade",
    "cross",
    "checkerboard",
    "loading",
    "spotlight",
    "starburst",
    "strobe",
    "glitch",
    "bounce",
    "orbit",
    "scan",
    "wipe",
    "snake",
    "basic",
    "breathe",
    "matrix",
    "conway",
    "drop",
    "spiral",
]


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


def reachable_sums(basis: list[int], max_val: int) -> set[int]:
    """all values expressible as a sum of a subset of basis values."""
    sums = {0}
    for b in basis:
        sums |= {s + b for s in sums if s + b <= max_val}
    return sums


def find_basis(targets: set[int], max_size: int = MAX_BASIS_SIZE) -> list[int]:
    """find at most `max_size` non-zero basis values whose subset sums
    cover every target. uses GCD to shrink search space, then greedy selection.
    """
    g = reduce(gcd, targets)
    scaled = {t // g for t in targets}
    max_t = max(scaled)

    basis: list[int] = []
    uncovered = scaled - {0}

    while uncovered and len(basis) < max_size:
        best_val, best_count = -1, 0
        for candidate in range(1, max_t + 1):
            if candidate in basis:
                continue
            covered = len(uncovered & reachable_sums(basis + [candidate], max_t))
            if covered > best_count:
                best_count = covered
                best_val = candidate

        if best_val == -1:
            break
        basis.append(best_val)
        uncovered -= reachable_sums(basis, max_t)

    return sorted(b * g for b in basis)


def decompose(target: int, basis: list[int]) -> list[int] | None:
    """find a subset of basis indices whose values sum to target."""
    if target == 0:
        return []

    def backtrack(remaining: int, start: int, path: list[int]) -> list[int] | None:
        if remaining == 0:
            return path[:]
        for i in range(start, len(basis)):
            if basis[i] > remaining:
                break
            path.append(i)
            result = backtrack(remaining - basis[i], i + 1, path)
            if result is not None:
                return result
            path.pop()
        return None

    return backtrack(target, 0, [])


def pack_frame(delay_indices: list[int], grid: list[list[int]]) -> int:
    """pack a frame into a single 32-bit integer."""
    flags = 0
    for i in delay_indices:
        flags |= 1 << (31 - i)
    for r, row in enumerate(grid):
        for c, val in enumerate(row):
            if val:
                flags |= 1 << (24 - r * 5 - c)
    return flags


def verify(
    basis: list[int],
    everything: list[int],
    anim_ranges: dict[str, tuple[int, int]],
    animations: dict[str, list[tuple[int, list[list[int]]]]],
) -> bool:
    """decode every packed frame and diff against the original animations."""
    ok = True
    for name in sorted(anim_ranges):
        start, end = anim_ranges[name]
        original = animations[name]
        if end - start != len(original):
            print(
                error(
                    f"  {name}: frame count mismatch ({end - start} vs {len(original)})"
                )
            )
            ok = False
            continue
        for i, packed in enumerate(everything[start:end]):
            delay = sum(basis[b] for b in range(len(basis)) if (packed >> (31 - b)) & 1)
            grid = [
                [(packed >> (24 - r * 5 - c)) & 1 for c in range(5)] for r in range(5)
            ]
            orig_delay, orig_grid = original[i]
            if delay != orig_delay or grid != orig_grid:
                print(
                    error(f"  {name} frame {i}: expected {orig_delay}ms, got {delay}ms")
                )
                ok = False
    return ok


def main() -> None:
    excluded_names = list(set(EXCLUDED_ANIMATIONS))
    animations, excluded_found, excluded_missing = collect_animations(excluded_names)
    animations, clean_stats = cleaner.clean_all(animations)
    timings = {t for anim in animations.values() for t, _ in anim}

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
        for s in clean_stats:
            print(
                f"  {success(str(s['name']))}: {s['before']} -> {s['after']} "
                f"(trimmed {s['trimmed']}, bytes saved {s['bytes_saved']})"
            )
        print()

    g = reduce(gcd, timings)
    print(f"{key('GCD')}: {g}ms")

    basis = find_basis(timings)
    print(f"{heading(f'basis ({len(basis)} slots)')}: {basis}")

    missing = timings - reachable_sums(basis, max(timings))
    if missing:
        print(
            f"\n{error('FAILED')} {warning('unreachable timings')}: {sorted(missing)}"
        )
        return
    print(f"\n{success(f'all {len(timings)} timings are reachable')}\n")

    # encode all frames as packed 32-bit values
    everything: list[int] = []
    anim_ranges: dict[str, tuple[int, int]] = {}

    for name in sorted(animations):
        start = len(everything)
        for i, (delay, grid) in enumerate(animations[name]):
            indices = decompose(delay, basis)
            if indices is None:
                raise ValueError(f"can't decompose {name} frame {i}: {delay}ms")
            everything.append(pack_frame(indices, grid))
        anim_ranges[name] = (start, len(everything))

    if verify(basis, everything, anim_ranges, animations):
        print(success("round-trip verification passed\n"))
    else:
        print(error("round-trip verification FAILED"))
        return

    start_indices = [anim_ranges[n][0] for n in sorted(anim_ranges)]
    total_frames = len(everything)
    total_anim_bytes = total_frames * 4

    # print summary table
    nw = max(4, *(len(n) for n in anim_ranges))
    iw = len(str(total_frames))
    print(
        f"  {info('name'):<{nw}}  {'range':>{2 * iw + 4}}  {'frames':>6}  {'bytes':>5}  {'%':>7}"
    )
    print(muted("  " + "-" * (nw + 2 * iw + 28)))
    for name, (s, e) in anim_ranges.items():
        fc, bc = e - s, (e - s) * 4
        pct = bc / total_anim_bytes * 100 if total_anim_bytes else 0
        print(
            f"  {info(name):<{nw + 9}}  {accent(f'[{s:>{iw}}, {e:>{iw}})'):<{2 * iw + 13}}"
            f"  {key(f'{fc:>6}')}  {warning(f'{bc:>5}')}  {alert(f'{pct:6.2f}%')}"
        )

    # write packed payload
    def _arr(out, label: str, vals: list[int], fmt: Callable[[int], str] = str) -> None:
        out.write(f"# {label}: \n{{{','.join(fmt(v) for v in vals)}}}\n\n")

    with open("encoded.dat", "w") as f:
        _arr(f, "basis", basis)
        _arr(f, "start_indices", start_indices)
        _arr(f, "everything", everything, lambda v: f"0b{v:032b}")
        _arr(f, "everything_hex", everything, lambda v: f"0x{v:08x}")
        _arr(f, "everything_int", everything)

    with open("encoded.bin", "wb") as bf:
        for v in everything:
            bf.write(v.to_bytes(length=4))

    print(success("\nall data written to encoded.dat and encoded.bin\n"))

    idx_bytes = len(anim_ranges)
    basis_bytes = len(basis)
    total = total_anim_bytes + idx_bytes + basis_bytes

    print(heading("Memory Footprint:"))
    print(
        f"  {key('Animation Data (32-bit frames)')}: {total_anim_bytes} bytes ({total_frames} frames)"
    )
    print(
        f"  {key('Start Indices (8-bit)')}:          {idx_bytes} bytes ({len(anim_ranges)} animations)"
    )
    print(f"  {key('Basis Array (8-bit)')}:            {basis_bytes} bytes")
    print(f"  {muted('-' * 45)}")
    print(f"  {warning('Total Required Memory')}:          {total} bytes")


if __name__ == "__main__":
    main()
