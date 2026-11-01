"""Keep the app's memory flat: limit glibc's malloc arenas from inside the process.

Measured on a GitHub runner (evals/results/footprint-soak*.json): asking one
question of each of the 32 filings ten times over, resident memory climbed
from 1.46 GB to 1.84 GB with glibc's default arenas and never levelled off,
while with MALLOC_ARENA_MAX=2 it stayed between 0.69 and 0.73 GB at the same
speed. LanceDB, Arrow and ONNX Runtime allocate from many threads; each new
thread can get its own arena, and freed memory fragments across them rather
than returning to the system. Not a leak, and not the index (93 MB).

Streamlit Community Cloud offers no way to set an environment variable before
Python starts, and glibc reads MALLOC_ARENA_MAX only then. mallopt(M_ARENA_MAX)
sets the same limit at run time for arenas created afterwards, so it is called
first thing in streamlit_app.py, before any library starts its threads.
"""

from __future__ import annotations

import ctypes
import ctypes.util

M_ARENA_MAX = -8  # glibc's malloc.h
ARENAS = 2


def limit_malloc_arenas(arenas: int = ARENAS) -> bool:
    """Ask glibc to create at most `arenas` malloc arenas; False where there is no glibc (macOS)."""
    name = ctypes.util.find_library("c")
    if not name:
        return False
    try:
        return bool(ctypes.CDLL(name).mallopt(M_ARENA_MAX, arenas))
    except (OSError, AttributeError):
        return False
