"""small ANSI helpers for readable CLI output."""

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _wrap(text: str, *codes: str) -> str:
    if not _USE_COLOR:
        return text
    return "".join(codes) + text + RESET


def heading(text: str) -> str:
    return _wrap(text, BOLD, MAGENTA)


def key(text: str) -> str:
    return _wrap(text, CYAN)


def info(text: str) -> str:
    return _wrap(text, BLUE)


def success(text: str) -> str:
    return _wrap(text, GREEN)


def warning(text: str) -> str:
    return _wrap(text, YELLOW)


def accent(text: str) -> str:
    return _wrap(text, MAGENTA)


def alert(text: str) -> str:
    return _wrap(text, RED)


def error(text: str) -> str:
    return _wrap(text, RED, BOLD)


def muted(text: str) -> str:
    return _wrap(text, DIM)


def bits(bit_string: str) -> str:
    if not _USE_COLOR:
        return bit_string
    out: list[str] = []
    for ch in bit_string:
        if ch == "1":
            out.append(success(ch))
        elif ch == "0":
            out.append(muted(ch))
        else:
            out.append(ch)
    return "".join(out)
