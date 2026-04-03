"""clean animations by trimming repeated full cycles."""

import sys
from pathlib import Path

import interpret
from ansi import heading, key, muted, success, warning

ROWS = 5
ANIM_DIR = Path(__file__).resolve().with_name("animations")
ADVISORY_MIN_SIMILARITY = 0.85
ADVISORY_MIN_TRIMMED_FRAMES = 2


def _find_cycle_period(animation: list[tuple[int, list[list[int]]]]) -> int | None:
    total = len(animation)
    if total < 2:
        return None

    period = 1
    while period < total:
        if total % period != 0:
            period += 1
            continue

        ok = True
        i = 0
        while i < total:
            if animation[i] != animation[i % period]:
                ok = False
                break
            i += 1

        if ok:
            return period
        period += 1
    return None


def _best_similarity_period(
    animation: list[tuple[int, list[list[int]]]]
) -> tuple[int, float, list[int]] | None:
    total = len(animation)
    if total < 2:
        return None

    best_period = -1
    best_ratio = -1.0
    best_mismatches: list[int] = []

    period = 1
    while period < total:
        matches = 0
        mismatches: list[int] = []
        i = 0
        while i < total:
            if animation[i] == animation[i % period]:
                matches += 1
            else:
                mismatches.append(i)
            i += 1
        ratio = matches / total
        if ratio > best_ratio:
            best_ratio = ratio
            best_period = period
            best_mismatches = mismatches
        period += 1

    return best_period, best_ratio, best_mismatches


def clean_animation(
    animation: list[tuple[int, list[list[int]]]]
) -> tuple[list[tuple[int, list[list[int]]]], int]:
    """trim repeated full cycles from one animation."""
    period = _find_cycle_period(animation)
    if period is None:
        return animation, 0
    trimmed = len(animation) - period
    if trimmed <= 0:
        return animation, 0
    return animation[:period], trimmed


def clean_all(
    animations: dict[str, list[tuple[int, list[list[int]]]]]
) -> tuple[dict[str, list[tuple[int, list[list[int]]]]], list[dict[str, int]]]:
    """clean all animations and return per-animation stats."""
    cleaned: dict[str, list[tuple[int, list[list[int]]]]] = {}
    stats: list[dict[str, int]] = []

    for name in sorted(animations.keys()):
        original = animations[name]
        result, trimmed = clean_animation(original)
        cleaned[name] = result
        if trimmed > 0:
            stats.append(
                {
                    "name": name,
                    "before": len(original),
                    "after": len(result),
                    "trimmed": trimmed,
                    "rows_saved": trimmed * ROWS,
                    "bytes_saved": trimmed * ROWS,
                }
            )

    return cleaned, stats


def advisory_report(
    animations: dict[str, list[tuple[int, list[list[int]]]]],
    *,
    broad: bool = False,
) -> list[dict[str, object]]:
    """detect near-periodic animations for manual review."""
    advisories: list[dict[str, object]] = []

    for name in sorted(animations.keys()):
        animation = animations[name]
        total = len(animation)
        if total < 2:
            continue

        exact_period = _find_cycle_period(animation)
        best = _best_similarity_period(animation)
        if best is None:
            continue

        period, ratio, mismatches = best

        # report only non-exact cases as advisory.
        if exact_period is not None:
            continue
        if ratio < ADVISORY_MIN_SIMILARITY:
            continue

        possible_trimmed = total - period
        if possible_trimmed <= 0:
            continue
        if not broad and possible_trimmed < ADVISORY_MIN_TRIMMED_FRAMES:
            continue

        if ratio >= 0.95:
            level = "high"
        elif ratio >= 0.90:
            level = "medium"
        else:
            level = "low"
        if not broad and level == "low":
            continue

        advisories.append(
            {
                "name": name,
                "level": level,
                "frames": total,
                "candidate_period": period,
                "similarity_ratio": ratio,
                "mismatch_count": len(mismatches),
                "mismatches": mismatches[:10],
                "possible_trimmed": possible_trimmed,
                "possible_bytes_saved": possible_trimmed * ROWS,
            }
        )

    return advisories


def _load_all_from_files() -> dict[str, list[tuple[int, list[list[int]]]]]:
    animations: dict[str, list[tuple[int, list[list[int]]]]] = {}
    paths = sorted(ANIM_DIR.glob("*.anim"))
    for path in paths:
        with open(path) as f:
            animations[path.stem] = interpret.parse_text(f.read())
    return animations


def main() -> None:
    broad = "--broad" in sys.argv
    animations = _load_all_from_files()
    cleaned, stats = clean_all(animations)
    advisories = advisory_report(animations, broad=broad)

    total_before = 0
    total_after = 0
    for name in cleaned:
        total_before += len(animations[name])
        total_after += len(cleaned[name])

    print(f"{key('animations')}: {len(animations)}")
    print(f"{key('cleaned')}: {len(stats)}")
    print(f"{key('advisories')}: {len(advisories)}")
    print()
    if not broad:
        print(warning("usage: python cleaner.py [--broad]"))
        print()

    if stats:
        print(heading("trimmed animations:"))
        for item in stats:
            print(
                f"  {success(item['name'])}: {item['before']} -> {item['after']} "
                f"(trimmed {item['trimmed']}, bytes saved {item['bytes_saved']})"
            )
        print()
    else:
        print(f"{heading('trimmed animations')}: {muted('none')}")
        print()

    if advisories:
        print(heading("advisory candidates (manual review):"))
        print(
            f"  {muted('meaning')}: cycle=len of best repeating chunk, "
            "match=percent of frames fitting that cycle"
        )
        print(
            f"  {muted('mismatches')}: frame indices that break the pattern, "
            "possible save=trim to candidate cycle length"
        )
        for item in advisories:
            ratio = float(item["similarity_ratio"]) * 100.0
            print(
                f"  {warning(item['name'])} [{item['level']}]: "
                f"cycle={item['candidate_period']}f, "
                f"match={ratio:.2f}%, "
                f"mismatches={item['mismatch_count']} @ {item['mismatches']}, "
                f"possible save={item['possible_trimmed']}f/"
                f"{item['possible_bytes_saved']}B"
            )
        print()
    else:
        print(f"{heading('advisory candidates')}: {muted('none')}")
        print()
        if not broad:
            print(warning("tip: use --broad for lower-impact advisories"))
            print()

    actual_frames_saved = total_before - total_after
    actual_rows_saved = actual_frames_saved * ROWS
    actual_bytes_saved = actual_rows_saved
    actual_percent = 0.0
    if total_before > 0:
        actual_percent = (actual_frames_saved / total_before) * 100.0

    advisory_frames_saved = 0
    advisory_bytes_saved = 0
    for item in advisories:
        advisory_frames_saved += int(item["possible_trimmed"])
        advisory_bytes_saved += int(item["possible_bytes_saved"])

    possible_frames_saved = actual_frames_saved + advisory_frames_saved
    possible_rows_saved = possible_frames_saved * ROWS
    possible_bytes_saved = actual_bytes_saved + advisory_bytes_saved
    possible_percent = 0.0
    if total_before > 0:
        possible_percent = (possible_frames_saved / total_before) * 100.0

    print(heading("totals:"))
    print(f"  {key('actual')}:")
    print(
        f"    frames: {total_before} -> {total_after} "
        f"(saved {actual_frames_saved})"
    )
    print(f"    rows saved: {actual_rows_saved}")
    print(f"    bytes saved in everything: {actual_bytes_saved}")
    print(f"    frame reduction: {actual_percent:.2f}%")
    print(f"  {key('possible')} (actual + shown advisories):")
    print(
        f"    frames saved: {possible_frames_saved} "
        f"({actual_frames_saved} actual + {advisory_frames_saved} advisory)"
    )
    print(f"    rows saved: {possible_rows_saved}")
    print(
        f"    bytes saved in everything: {possible_bytes_saved} "
        f"({actual_bytes_saved} actual + {advisory_bytes_saved} advisory)"
    )
    print(f"    frame reduction: {possible_percent:.2f}%")


if __name__ == "__main__":
    main()
