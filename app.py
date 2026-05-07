"""
app.py — Streamlit demo UI for the Content Pipeline.
Supports Smart Fog (content plan flow) and Veriheal (URL flow).

Run locally:  streamlit run app.py
Deploy:       Streamlit Cloud — set API keys as secrets, uses Procfile for startup.
"""

from __future__ import annotations
import os
import re
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st
from docx import Document

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Page config  (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Content Pipeline",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
_STATE_DEFAULTS: dict = {
    "article_path": None,
    "brief_path": None,
    "last_client": None,
    "is_running": False,
    "last_generated_name": None,
    "last_generated_time": None,
    "error_message": None,
    "current_stage_num": 0,
    "total_stages": 6,
}
for _k, _v in _STATE_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_para_text(para) -> str:
    """Extract paragraph text, rendering Word hyperlinks as markdown [anchor](url)."""
    try:
        from lxml import etree
        W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        parts = []
        for child in para._p:
            local = etree.QName(child).localname
            if local == "hyperlink":
                r_id = child.get(f"{{{R}}}id")
                anchor = "".join((t.text or "") for t in child.findall(f".//{{{W}}}t"))
                if r_id and hasattr(para.part, "rels") and r_id in para.part.rels:
                    url = para.part.rels[r_id].target_ref
                    parts.append(f"[{anchor}]({url})" if url else anchor)
                else:
                    parts.append(anchor)
            elif local == "r":
                parts.append("".join((t.text or "") for t in child.findall(f".//{{{W}}}t")))
        return "".join(parts).strip()
    except Exception:
        return para.text.strip()


def _read_docx_for_display(path: Path) -> str:
    """Extract text from a docx with markdown headings and live hyperlinks."""
    try:
        doc = Document(str(path))
        lines = []
        for p in doc.paragraphs:
            txt = _extract_para_text(p)
            if not txt:
                continue
            style = p.style.name
            if "Heading 1" in style:
                lines.append(f"# {txt}")
            elif "Heading 2" in style:
                lines.append(f"## {txt}")
            elif "Heading 3" in style:
                lines.append(f"### {txt}")
            elif "List" in style:
                lines.append(f"- {txt}")
            else:
                lines.append(txt)
        return "\n\n".join(lines)
    except Exception as e:
        return f"Could not render document: {e}"


def _word_count(path: Path) -> int:
    """Count words in a docx file."""
    try:
        doc = Document(str(path))
        text = " ".join(p.text for p in doc.paragraphs)
        return len(text.split())
    except Exception:
        return 0


def _latest_output(client_key: str, kind: str) -> Path | None:
    """Return the most recently modified brief or article docx for a client."""
    output_dir = ROOT / "outputs" / client_key
    if not output_dir.exists():
        return None
    all_docx = [f for f in output_dir.glob("*.docx") if not f.name.startswith("_")]
    if kind == "brief":
        files = [f for f in all_docx if f.name.lower().startswith("brief")]
    else:
        files = [f for f in all_docx if not f.name.lower().startswith("brief")]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0] if files else None


def _load_smart_fog_rows() -> list[tuple[int, str, str]]:
    """Return [(row_index, topic, keyword), ...] from the Smart Fog content plan."""
    try:
        import config as cfg
        profile = cfg.load_client_profile("smart-fog")
        cp_config = profile.get("content_plan", {})
        excel_path = os.path.join(
            cfg.ROOT_DIR,
            cp_config.get("excel_path", "inputs/smart-fog/Smart Fog Content Plan.xlsx"),
        )
        from pipeline.content_plan_parser import parse_content_plan
        rows = parse_content_plan(
            excel_path, row_index=None, tab_name=None, profile=profile
        )
        return [
            (
                int(r.get("content_plan_row", i)),
                r.get("content_plan_topic", "")[:80],
                r.get("content_plan_primary_keyword", ""),
            )
            for i, r in enumerate(rows)
            if r.get("content_plan_primary_keyword")
        ]
    except Exception as e:
        st.error(f"Could not load content plan: {e}")
        return []


def _run_pipeline(args: list[str]):
    """Run main.py as a subprocess, yielding stdout lines in real time."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "main.py")] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(ROOT),
        env=env,
    )
    for line in proc.stdout:
        yield line.rstrip()
    proc.wait()
    return proc.returncode


def _download_button(path: Path, label: str):
    with open(path, "rb") as f:
        st.download_button(
            label=label,
            data=f.read(),
            file_name=path.name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Sidebar — client selector + pipeline stages + last generated
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ✍️ Content Pipeline")
    st.markdown("---")

    client_display = st.radio(
        "Client",
        ["Smart Fog", "Veriheal"],
        index=0,
        disabled=st.session_state.is_running,
    )
    client_key = "smart-fog" if client_display == "Smart Fog" else "veriheal"

    st.markdown("---")

    # Pipeline stages — highlight current stage during a run
    _smart_fog_stages = [
        "Parse content plan",
        "Ahrefs keyword research",
        "Competitor analysis",
        "NeuronWriter NLP terms",
        "Brief generation",
        "Article generation",
    ]
    _veriheal_stages = [
        "Scrape article URL",
        "GSC data",
        "Ahrefs keyword research",
        "Competitor analysis",
        "NeuronWriter NLP terms",
        "Brief generation",
        "Article generation",
    ]
    _stages = _smart_fog_stages if client_display == "Smart Fog" else _veriheal_stages
    # Pipeline uses 7-stage numbering; Smart Fog skips 1 & 2 so offset by 2
    _stage_offset = 2 if client_display == "Smart Fog" else 0
    _cur_pipeline = st.session_state.current_stage_num  # pipeline's X/7 number
    _cur_ui = max(0, _cur_pipeline - _stage_offset)     # mapped to UI list index

    st.caption("Pipeline stages")
    for _i, _stage in enumerate(_stages, start=1):
        if st.session_state.is_running and _i == _cur_ui:
            st.markdown(f"**→ {_i} · {_stage}**")
        elif st.session_state.is_running and _i < _cur_ui:
            st.caption(f"✓ {_i} · {_stage}")
        else:
            st.caption(f"{_i} · {_stage}")

    # Last generated indicator
    if st.session_state.last_generated_name:
        st.markdown("---")
        st.caption("Last generated")
        st.caption(f"📄 {st.session_state.last_generated_name}")
        if st.session_state.last_generated_time:
            st.caption(f"🕐 {st.session_state.last_generated_time}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("✍️ Content Pipeline")
st.caption("Automated brief and article generation — select a client and input, then hit Generate.")

st.divider()

run_args: list[str] = []

# --- Smart Fog ---
if client_display == "Smart Fog":
    st.subheader("Smart Fog — Content Plan")
    rows = _load_smart_fog_rows()
    if rows:
        options = {
            topic if topic else f"Row {idx}": idx
            for idx, topic, kw in rows
        }
        selected_label = st.selectbox(
            "Select article from content plan",
            list(options.keys()),
            help="Rows are pulled live from the Smart Fog Content Plan Excel file.",
            disabled=st.session_state.is_running,
        )
        selected_row = options[selected_label]
        selected_kw = next(kw for idx, _, kw in rows if idx == selected_row)
        # Show full title in case selectbox truncates
        if len(selected_label) > 60:
            st.caption(f"📌 {selected_label}")
        st.caption(f"Primary keyword: **{selected_kw}**")
        run_args = ["--client", "smart-fog", "--row", str(selected_row)]
    else:
        row_num = st.number_input("Row number", min_value=0, value=0, step=1,
                                   disabled=st.session_state.is_running)
        run_args = ["--client", "smart-fog", "--row", str(row_num)]

# --- Veriheal ---
else:
    st.subheader("Veriheal — Article Optimisation")
    url = st.text_input(
        "Article URL",
        placeholder="https://www.veriheal.com/blog/...",
        help="Enter the full URL of an existing Veriheal article to optimise.",
        disabled=st.session_state.is_running,
    )
    _url = url.strip()
    if _url:
        if "veriheal.com" not in _url:
            st.warning("URL should be a veriheal.com article.")
        else:
            run_args = ["--client", "veriheal", "--url", _url]
    else:
        st.info("Enter an article URL to continue.")

# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
st.divider()

col_btn, col_note = st.columns([2, 5])
with col_btn:
    generate = st.button(
        "🚀 Generate Brief + Article",
        type="primary",
        disabled=not run_args or st.session_state.is_running,
        use_container_width=True,
    )
with col_note:
    st.caption("⏱ Avg generation time: 6–8 min")
    if st.session_state.is_running:
        st.caption("⚙️ Pipeline is running — please wait...")

# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------
if generate and run_args and not st.session_state.is_running:
    st.session_state.is_running = True
    st.session_state.article_path = None
    st.session_state.brief_path = None
    st.session_state.last_client = client_key
    st.session_state.error_message = None
    st.session_state.current_stage_num = 0

    start_time = time.time()
    os.makedirs(ROOT / "outputs" / client_key, exist_ok=True)

    log_lines: list[str] = []
    error_lines: list[str] = []
    progress_bar = st.progress(0.0, text="Starting pipeline...")
    stage_label = st.empty()
    log_placeholder = st.empty()

    _total = len(_smart_fog_stages) if client_display == "Smart Fog" else len(_veriheal_stages)
    st.session_state.total_stages = _total

    with st.status("Pipeline running...", expanded=True) as status:
        for line in _run_pipeline(run_args):
            if not line.strip():
                continue

            # Detect stage markers — pipeline always prints "Stage X / 7 — Name"
            # inside a banner block. The stage name is on the indented line between ===.
            _stage_match = re.search(r'Stage\s+(\d+)\s*/\s*(\d+)\s*[—-]+\s*(.*)', line)
            if _stage_match:
                _cur_n = int(_stage_match.group(1))
                _tot_n = int(_stage_match.group(2))
                _stage_name = _stage_match.group(3).strip()
                st.session_state.current_stage_num = _cur_n
                _pct = (_cur_n - 1) / _tot_n
                progress_bar.progress(_pct, text=f"Stage {_cur_n}/{_tot_n} — {_stage_name}")
                stage_label.markdown(f"**⚙️ Stage {_cur_n}/{_tot_n} — {_stage_name}**")
                continue

            if "===" in line:
                continue

            # Detect errors
            _low = line.lower()
            if any(k in _low for k in ("error", "failed", "critical", "traceback", "exception")):
                error_lines.append(line.strip())

            log_lines.append(line.strip())
            log_placeholder.code("\n".join(log_lines[-20:]), language=None)

        elapsed = time.time() - start_time
        progress_bar.progress(1.0, text="Complete")

        if error_lines and not _latest_output(client_key, "article"):
            st.session_state.error_message = error_lines[-1]
            status.update(label=f"❌ Pipeline failed after {elapsed:.0f}s", state="error", expanded=True)
        else:
            status.update(label=f"✅ Done in {elapsed:.0f}s", state="complete", expanded=False)

    # Store outputs and metadata in session state
    _art = _latest_output(client_key, "article")
    _brf = _latest_output(client_key, "brief")
    st.session_state.article_path = str(_art) if _art else None
    st.session_state.brief_path = str(_brf) if _brf else None
    st.session_state.current_stage_num = 0
    st.session_state.is_running = False

    if _art:
        st.session_state.last_generated_name = _art.stem[:50]
        st.session_state.last_generated_time = datetime.now().strftime("%d %b %Y, %H:%M")

    st.rerun()

# ---------------------------------------------------------------------------
# Error display
# ---------------------------------------------------------------------------
if st.session_state.error_message and not st.session_state.article_path:
    st.error(f"Pipeline failed: {st.session_state.error_message}")
    st.caption("Check the log above for the full trace, fix the issue, and re-run.")

# ---------------------------------------------------------------------------
# Output display — persists across interactions via session state
# ---------------------------------------------------------------------------
if st.session_state.article_path or st.session_state.brief_path:
    st.divider()
    st.subheader("Generated outputs")

    article_path = Path(st.session_state.article_path) if st.session_state.article_path else None
    brief_path = Path(st.session_state.brief_path) if st.session_state.brief_path else None

    # Word count badge
    _wc = _word_count(article_path) if article_path and article_path.exists() else 0
    _wc_label = f" · {_wc:,} words" if _wc else ""

    tab_article, tab_brief = st.tabs([f"📄 Article{_wc_label}", "📋 Brief"])

    with tab_article:
        if article_path and article_path.exists():
            col_dl, col_info = st.columns([1, 4])
            with col_dl:
                _download_button(article_path, "⬇️ Download Article (.docx)")
            with col_info:
                st.caption(f"File: `{article_path.name}`")
                if st.session_state.last_generated_time:
                    st.caption(f"Generated: {st.session_state.last_generated_time}")
            st.divider()
            st.markdown(_read_docx_for_display(article_path))
        else:
            st.warning("No article file found. Check the pipeline log above for errors.")

    with tab_brief:
        if brief_path and brief_path.exists():
            col_dl, col_info = st.columns([1, 4])
            with col_dl:
                _download_button(brief_path, "⬇️ Download Brief (.docx)")
            with col_info:
                st.caption(f"File: `{brief_path.name}`")
            st.divider()
            st.markdown(_read_docx_for_display(brief_path))
        else:
            st.warning("No brief file found. Check the pipeline log above for errors.")
