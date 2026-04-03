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

The encoded data will be what the chip sees. Right now, the current encoding is **proposed**.

`encode.py` converts all `.anim` files into three arrays in `encoded.dat`:

1. `basis`: small timing lookup table (max 8 entries, index fits in 3 bits).
2. `start_indices`: start row index for each animation in encoded order.
3. `everything`: flat byte array, one byte per LED row.

Each encoded row byte is:

- upper 3 bits: timing basis index
- lower 5 bits: LED row bits

For a frame (5 rows):

- row delays are looked up from `basis` using each row's upper 3 bits
- frame delay is the sum of those 5 basis values
- row pixels come from the lower 5 bits of each row byte

The decoder is designed to match intended chip-side behavior: timing and pixels are decoded directly from packed row bytes.

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
