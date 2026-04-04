# Art

Contains everything used to develop and test animations.

## Directory Structure

- [animations/](animations/): Source `*.anim` files.
- [ansi.py](ansi.py): Helper for colorizing output.
- [interpret.py](interpret.py): Pure parser for `.anim` text (`parse_lines` / `parse_text`).
- [encode.py](encode.py): Packs all animations into the format the chip will use.
- [encoded.dat](encoded.dat): Generated encoded payload consumed by the decoder.
- [decoder.py](decoder.py): Decodes `encoded.dat` into `{name: Animation}`.
- [cleaner.py](cleaner.py): Very conservative cleaner of animations.
- [source.py](source.py): Single source switch for the simulator:
  - `ANIM_SOURCE=files` -> load from `animations/` via `interpret.py`
  - `ANIM_SOURCE=encoded` (default) -> load from `encoded.dat` via `decoder.py`
- [sim.py](sim.py): Tk simulator. Renders animations returned by `source.get_all()`.

## Animation Format

An `Animation` is:

- `list[tuple[int, grid]]`
- `int`: frame delay in milliseconds
- `grid`: 5x5 row-major list of `0/1` LED states

## Encoding Process

The encoded data will be what the chip sees.

`encode.py` converts all `.anim` files into three arrays in `encoded.dat`:

1. `basis`: small timing lookup table (max 7 entries).
2. `start_indices`: start frame index for each animation in encoded order.
3. `everything`: flat 32-bit integer array, one 32-bit integer per frame.

Each encoded 32-bit frame is packed as:

- upper 7 bits: boolean flags indicating which basis values to sum for the frame's delay
- lower 25 bits: the 5x5 LED grid, flattened row by row

For a frame (32 bits):

- frame delay is the sum of the `basis` values whose corresponding flag bit is set in the top 7 bits
- grid pixels are extracted from the lower 25 bits

The decoder is designed to match intended chip-side behavior: timing and pixels are decoded directly from packed 32-bit frames.

## Workflow

### Creation

1. Edit animations in `animations/`.
2. Run `sim.py` with `ENCODED` and `CLEAN` set to `False`.
3. Repeat steps 1 and 2 until satisfied with all animations.
4. Run `sim.py` with `ENCODED=False` and `CLEAN=True` to verify that cleaning doesn't mess anything up.

Once animations look good, move on to finalizing.

### Finalizing

1. Run `encode.py`.
2. Run `sim.py` with `ENCODED=True` and verify all animations. If you don't like cleaned, then comment out the cleaning line.
3. Transfer into the chip's code.
