"""Entry point for `streamlit run streamlit_app.py`, locally and on Community Cloud.

`streamlit run` puts only the script's own folder on the import path. Run as
ui/app.py, that folder is ui/, so `gen` and `retrieve` cannot be imported and
the app dies on its first line; `python -m streamlit` hid this locally by adding
the working directory. Living at the repo root makes every package importable
under either launcher, and it is the filename Community Cloud fills in.
"""

# First, before any library starts threads: keeps memory flat (ui/memory.py).
from ui.memory import limit_malloc_arenas

limit_malloc_arenas()

from ui.app import main  # noqa: E402

main()
