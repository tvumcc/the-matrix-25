"""single animation source for the simulator.

can source from encoded files (using decoder)
or from the animations directory (using interpret).

uses ENCODED to determine the source.
"""

from pathlib import Path

ROWS = 5
COLS = 5
ANIM_DIR = Path(__file__).resolve().with_name("animations")
ENCODED = True
CLEAN = True


def _get_all_from_files() -> dict[str, list[tuple[int, list[list[int]]]]]:
    import cleaner
    import interpret

    animations: dict[str, list[tuple[int, list[list[int]]]]] = {}
    paths = sorted(ANIM_DIR.glob("*.anim"))
    for path in paths:
        name = path.stem
        with open(path) as f:
            text = f.read()
        animations[name] = interpret.parse_text(text)

    # set to false to skip cleaning.
    if CLEAN:
        print("cleaning filesystem animations")
        animations, _stats = cleaner.clean_all(animations)
    return animations


def get_all() -> dict[str, list[tuple[int, list[list[int]]]]]:
    """return all animations as {name: Animation}."""
    if ENCODED:
        print("using encoded animations")
        import decoder

        return decoder.get_all()
    else:
        print("using filesystem animations")
        return _get_all_from_files()
