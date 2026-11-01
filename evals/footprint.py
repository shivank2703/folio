"""Measure what the app costs to start and to hold: time and memory per stage.

Streamlit Community Cloud gives an app about 2.7 GB of memory and puts it to
sleep after inactivity, so every wake is a cold start. This replays the app's
own startup in one process — imports, index fetch, index open, embedding
model, then a question per filing (search, page packing, the per-filing
spelling vocabulary) and the stored data files — and records wall time and
resident memory after each stage. It calls no model API.

    python -m evals.footprint --out evals/results/footprint.json

The index fetch is timed into a fresh directory, as on a new container; the
stages after it use the normal data/lancedb. Without the embedding model
(a sandbox that cannot download it) the model stages are skipped and said to be.
"""

from __future__ import annotations

import argparse
import json
import resource
import shutil
import tempfile
import time
from pathlib import Path

STAGES: list[dict] = []
STARTED = time.perf_counter()


def rss_mb() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return 0.0


def stage(name: str, seconds: float, note: str = "") -> None:
    STAGES.append({"stage": name, "seconds": round(seconds, 2), "rss_mb": round(rss_mb(), 1),
                   "peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "note": note})
    print(f"{name:<38} {seconds:7.2f}s  rss {STAGES[-1]['rss_mb']:7.1f} MB  peak {STAGES[-1]['peak_mb']:7.1f} MB  {note}",
          flush=True)


def timed(name: str, fn, note: str = ""):
    started = time.perf_counter()
    value = fn()
    stage(name, time.perf_counter() - started, note)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Time and memory of the app's startup and first questions.")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    def imports():
        import streamlit  # noqa: F401
        import ui.app  # noqa: F401  (the app's whole import graph)

    timed("imports (streamlit + app modules)", imports)
    from retrieve.search import DEFAULT_K, EXPANSION_SEEDS, open_index, page_context, search
    from retrieve.store import POINTER, ensure_index

    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        timed("index fetch + verify + unpack (fresh)", lambda: ensure_index(Path(tmp) / "lancedb"),
              f"{pointer['bytes'] / 1e6:.0f} MB tarball, {pointer['chunks']} chunks")
        unpacked = sum(f.stat().st_size for f in (Path(tmp) / "lancedb").rglob("*") if f.is_file())
    db = Path("data/lancedb")
    ensure_index(db)
    table = timed("open index", lambda: open_index(db), f"{unpacked / 1e6:.0f} MB on disk")

    try:
        from retrieve.embed import load_model
        model = timed("load embedding model", load_model)
    except Exception as error:  # the model host is unreachable here
        model = None
        stage("load embedding model", 0.0, f"SKIPPED: {type(error).__name__}")

    filings = json.loads(Path("corpus/corpus.json").read_text(encoding="utf-8"))
    try:
        from retrieve.spelling import vocabulary
    except ImportError:  # code from before misspelling correction existed
        vocabulary = None
    if vocabulary is not None:
        timed(f"spelling vocabularies ({len(filings)} filings)",
              lambda: [vocabulary(table, f["company"]) for f in filings], "the per-filing cache questions fill")
    if model is not None:
        first = filings[0]
        timed("first question (cold caches)", lambda: page_context(table, search(
            table, model, f"What were {first['name']}'s total assets?", max(DEFAULT_K, EXPANSION_SEEDS), first["company"])))

        def every_filing():
            for f in filings:
                hits = search(table, model, f"What was {f['name']}'s revenue in {f['fiscal_year']}?",
                              max(DEFAULT_K, EXPANSION_SEEDS), f["company"])
                page_context(table, hits)
        timed(f"one question per filing ({len(filings)})", every_filing)
        timed(f"the same {len(filings)} questions again", every_filing, "growth here would be per question, not per filing")
        timed(f"and a third time", every_filing, "levelling off here means caches, not a leak")

    def data_files():
        from funds.data import load_funds
        try:
            from overviews.build import load
        except ImportError:  # before overviews existed
            load = dict
        return load_funds(), load()
    timed("fund snapshots + overviews", data_files)

    result = {"measured": time.strftime("%Y-%m-%d %H:%M"), "index": pointer["asset"],
              "total_seconds": round(time.perf_counter() - STARTED, 2),
              "peak_mb": max(s["peak_mb"] for s in STAGES), "stages": STAGES,
              "model_loaded": model is not None}
    print(f"total {result['total_seconds']}s, peak {result['peak_mb']} MB of a 2,700 MB limit")
    if args.out:
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
