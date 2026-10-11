"""The maintainer's "Add a company" panel: ingest.add, publish and commit, from the app.

Shown only in an owner session (ui/limits.py): a visitor never sees it, so a
stranger cannot make the app fetch an arbitrary URL or write to the index.

Adding a company takes minutes (download, table reading, embedding), far
longer than a page request should hold, so it runs in a background thread
whose progress lives in the server process; the panel polls it. One job runs
at a time. The thread never calls Streamlit, it only writes to that state.

The result has to outlive the container, whose disk is reset by the next
restart or sleep. So the job ends the way a maintainer's terminal session
does: the index is uploaded as a release asset and the four record files are
committed to main in one commit, which also redeploys the app. Before
committing, it checks that main's copies of those files are the ones this
container started from: a container older than main would otherwise write its
stale copies over newer ones.
"""

from __future__ import annotations

import contextlib
import io
import threading
import time
import traceback
from pathlib import Path

import streamlit as st

RECORDS = ["corpus/urls.yaml", "corpus/corpus.json", "corpus/SOURCES.md", "corpus/index.json"]


@st.cache_resource(show_spinner=False)
def deployed_records() -> dict[str, str]:
    """The record files as this container started with them: what was deployed from main.

    Taken once per process, at the app's first page load. GitHub's main must
    still match it before a job commits, and a job that indexed a company but
    failed to save it can be retried, because its local records then differ
    from these.
    """
    return {path: Path(path).read_text(encoding="utf-8") for path in RECORDS}


@st.cache_resource(show_spinner=False)
def job() -> dict:
    """The one add-company job of this server process, shared by every session."""
    return {"lock": threading.Lock(), "running": False, "log": [], "stage": "", "outcome": None, "started": 0.0}


class _Log(io.TextIOBase):
    """Collects what ingest.add prints, line by line, for the panel to show."""

    def __init__(self, state: dict):
        self.state = state

    def write(self, text: str) -> int:
        for line in text.splitlines():
            if line.strip():
                self.state["log"].append(line.rstrip())
        return len(text)


def run(state: dict, code: str, entry: dict | None, model, on_index_changed) -> None:
    """Register (if new), ingest, publish and commit one company. Runs in a thread."""
    from ingest import github
    from ingest.add import add_one, register
    from ingest.publish import publish_index

    deployed = deployed_records()
    started_with = {path: Path(path).read_text(encoding="utf-8") for path in RECORDS}

    def stage(name: str) -> None:
        state["stage"] = name
        state["log"].append(f"— {name}")

    try:
        # print() from ingest.add lands in the panel. redirect_stdout is
        # process-wide, which is acceptable for a rare, maintainer-only job.
        with contextlib.redirect_stdout(_Log(state)):
            if entry is not None:
                stage("adding the company to corpus/urls.yaml")
                register(code, entry)
            stage("finding, checking and indexing the latest annual report")
            result = add_one(code, model)
            print(f"  {code}: {result}")
            changed = result.startswith(("added", "replaced", "re-indexed"))
            if changed:
                # Indexing pruned the old table version, and every session
                # shares one open handle to it: reopen it now, for everyone,
                # rather than when the owner's page next refreshes.
                on_index_changed()
            # An earlier job may have indexed the company and then failed to
            # save it; its records here then differ from what was deployed.
            unsaved = any(Path(path).read_text(encoding="utf-8") != deployed[path] for path in RECORDS[:3])
            if not changed and not unsaved:
                raise RuntimeError(result)

            stage("checking main has not moved since this app was deployed")
            for path, text in deployed.items():
                if github.file_text(path) != text:
                    raise RuntimeError(f"{path} on GitHub is newer than this app's copy; wait for the "
                                       "app to redeploy, then add the company again")
            stage("uploading the new index")
            pointer = publish_index()
            stage("saving to GitHub")
            files = {path: Path(path).read_text(encoding="utf-8") for path in RECORDS}
            sha = github.commit_files(files, f"Add {code}: {result} (from the app)\n\n"
                                             f"Index {pointer['asset']}, {pointer['chunks']} chunks.")
        state["outcome"] = ("ok", f"{code}: {result}. Saved as commit {sha[:7]}; the app redeploys in a "
                                  "few minutes with it in the Filing list everywhere.")
    except Exception as error:
        # Undo the local registration so a retry is not refused as a duplicate.
        Path(RECORDS[0]).write_text(started_with[RECORDS[0]], encoding="utf-8")
        state["log"].append(traceback.format_exc(limit=2).strip().splitlines()[-1])
        state["outcome"] = ("error", f"{code} was not added: {error}")
    finally:
        state["running"] = False


def start(code: str, entry: dict | None, model, on_index_changed) -> str | None:
    """Start a job unless one is running; return why not, if not."""
    state = job()
    with state["lock"]:
        if state["running"]:
            return "another company is being added; wait for it to finish"
        state.update(running=True, log=[], stage="starting", outcome=None, started=time.time())
    threading.Thread(target=run, args=(state, code, entry, model, on_index_changed), daemon=True).start()
    return None


@st.fragment(run_every=3)
def progress() -> None:
    """Poll the running job every few seconds; rerun the page once when it ends."""
    state = job()
    if state["running"]:
        st.info(f"Working ({time.time() - state['started']:.0f}s): {state['stage']}")
        st.code("\n".join(state["log"][-12:]) or "…", language=None)
    elif st.session_state.get("watching_job"):
        st.session_state["watching_job"] = False
        st.rerun()


def render(model, on_index_changed) -> None:
    """The panel itself. on_index_changed reopens the index and the Filing list for every session."""
    import yaml

    state = job()
    with st.expander("Add a company · maintainer only", expanded=state["running"]):
        if state["running"] or st.session_state.get("watching_job"):
            progress()
            return
        if state["outcome"]:
            kind, message = state["outcome"]
            (st.success if kind == "ok" else st.error)(message)
        st.caption("Finds the company's latest annual report, checks it is born-digital, indexes it "
                   "(3–10 minutes), uploads the new index and commits the record files to GitHub.")
        known = yaml.safe_load(Path(RECORDS[0]).read_text(encoding="utf-8")) or {}
        with st.form("add_company"):
            code = st.text_input("Company code", placeholder="e.g. UNIHEALTH (capitals and digits)").strip().upper()
            name = st.text_input("Company name", placeholder="e.g. Unihealth Hospitals (not needed if the code exists)")
            listing = st.text_input("Listing (optional)", placeholder="e.g. NSE SME UNIHEALTH")
            page = st.text_input("Investor page with the annual-report PDFs (optional)", placeholder="https://…")
            report = st.text_input("Or a direct annual-report PDF URL (optional)", placeholder="https://…pdf")
            go = st.form_submit_button("Add company")
        if not go:
            return
        entry = None
        if code not in known:
            urls = [u for u in (page, report) if u]
            if not name or not urls:
                st.error("A new company needs a name and at least one URL: its investor page or a report PDF.")
                return
            if any(not u.startswith("https://") for u in urls):
                st.error("URLs must start with https://")
                return
            entry = {"name": name.strip(), "listing": listing.strip(), "investor_page": page or None,
                     "reports": [{"url": report}] if report else []}
        why_not = start(code, entry, model, on_index_changed)
        if why_not:
            st.warning(why_not)
            return
        st.session_state["watching_job"] = True
        st.rerun()
