"""Delete index release assets that no commit names.

Every publish uploads a new tarball and leaves the old ones, so an older
commit can still fetch the index it was tested with (ingest/publish.py). An
asset that no commit's corpus/index.json has ever named — an in-app add that
uploaded and then failed to commit, a probe — serves no checkout and only
costs storage. This lists them, and deletes them only when asked:

    python -m ingest.prune            # dry run: what is kept, what would go, and why
    python -m ingest.prune --delete   # delete the unnamed ones (irreversible)

"Named" is read from every commit on every branch and tag the local clone
knows (`git fetch --all` first), so an asset a pushed branch points at is
kept. The release itself and every named asset are never touched.
"""

from __future__ import annotations

import argparse
import json
import subprocess

from ingest import github
from ingest.publish import RELEASE
from retrieve.store import POINTER


def named_assets() -> set[str]:
    """Every asset name any commit's corpus/index.json has pointed at, across all refs."""
    commits = subprocess.run(["git", "log", "--all", "--format=%H", "--", str(POINTER)],
                             capture_output=True, text=True, check=True).stdout.split()
    names = set()
    for commit in commits:
        shown = subprocess.run(["git", "show", f"{commit}:{POINTER}"], capture_output=True, text=True)
        if shown.returncode == 0:
            names.add(json.loads(shown.stdout)["asset"])
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete index release assets no commit names (dry run by default).")
    parser.add_argument("--delete", action="store_true", help="actually delete them; irreversible")
    args = parser.parse_args()
    named = named_assets()
    if not named:
        raise SystemExit(f"no commit names any asset; refusing to prune (is {POINTER} in this clone's history?)")
    for asset in github.release_assets(RELEASE):
        if asset["name"] in named:
            print(f"keep    {asset['name']}  ({asset['size'] / 1e6:.1f} MB, named by a commit)")
        elif args.delete:
            github.delete_asset(asset["id"])
            print(f"deleted {asset['name']}  ({asset['size'] / 1e6:.1f} MB)")
        else:
            print(f"would delete {asset['name']}  ({asset['size'] / 1e6:.1f} MB, created {asset['created_at']}, "
                  "named by no commit)")
    if not args.delete:
        print("dry run; run with --delete to remove the unnamed assets")


if __name__ == "__main__":
    main()
