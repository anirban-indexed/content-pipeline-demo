"""
app.py — Streamlit demo UI for the Content Pipeline.
Supports Smart Fog (content plan flow) and Veriheal (URL flow).

Run locally:  streamlit run app.py
Deploy:       Railway / Render — set API keys as env vars, uses Procfile for startup.
"""

from __future__ import annotations
import os
import sys
import time
import subprocess
from pathlib import Path

import streamlit as st
from docx import Document

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Content Pipeline",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_docx_for_display(path: Path) -> str:
    """Extract text from a docx with basic markdown-style heading markers."""
    try:
        doc = Document(str(path))
        lines = []
        for p in doc.paragraphs:
            txt = p.text.strip()
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


def _latest_output(client_key: str, prefix: str) -> Path | None:
    """Return the most recently modified output file matching the prefix."""
    output_dir = ROOT / "outputs" / client_key
    if not output_dir.exists():
        return None
    files = sorted(
        output_dir.glob(f"{prefix}_*.docx"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


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
                r.get("content_plan_topic", "")[:70],
                r.get("content_plan_primary_keyword", ""),
            )
            for i, r in enumerate(rows)
            if r.get("content_plan_primary_keyword")
        ]
    except Exception as e:
        st.error(f"Could not load content plan: {e}")
        return []


def _run_pipeline(args: list[str]):
    """Run main.py as a subprocess, yielding stdout lines."""
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "main.py")] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
        env={**os.environ},
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
# Sidebar — client selector
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.smartfog.com/wp-content/uploads/2021/07/smart-fog-logo.png", width=160)
    st.markdown("---")
    client_display = st.radio(
        "Client",
        ["Smart Fog", "Veriheal"],
        index=0,
    )
    client_key = "smart-fog" if client_display == "Smart Fog" else "veriheal"

    st.markdown("---")
    st.caption("Pipeline stages")
    st.caption("1 · Scrape / parse content plan")
    st.caption("2 · GSC data")
    st.caption("3 · Ahrefs keyword research")
    st.caption("4 · Competitor analysis")
    st.caption("5 · NeuronWriter NLP terms")
    st.caption("6 · Brief generation")
    st.caption("7 · Article generation")

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
            f"Row {idx}  ·  {topic}": idx
            for idx, topic, kw in rows
        }
        selected_label = st.selectbox(
            "Select article from content plan",
            list(options.keys()),
            help="Rows are pulled live from the Smart Fog Content Plan Excel file.",
        )
        selected_row = options[selected_label]
        selected_kw = next(kw for idx, _, kw in rows if idx == selected_row)
        st.caption(f"Primary keyword: **{selected_kw}**")
        run_args = ["--client", "smart-fog", "--row", str(selected_row)]
    else:
        row_num = st.number_input("Row number", min_value=0, value=0, step=1)
        run_args = ["--client", "smart-fog", "--row", str(row_num)]

# --- Veriheal ---
else:
    st.subheader("Veriheal — Article Optimisation")
    url = st.text_input(
        "Article URL",
        placeholder="https://www.veriheal.com/blog/...",
        help="Enter the full URL of an existing Veriheal article to optimise.",
    )
    if url.strip():
        run_args = ["--client", "veriheal", "--url", url.strip()]
    else:
        st.info("Enter an article URL to continue.")

# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
st.divider()
generate = st.button(
    "🚀 Generate Brief + Article",
    type="primary",
    disabled=not run_args,
    use_container_width=False,
)

if generate and run_args:
    start_time = time.time()
    os.makedirs(ROOT / "outputs" / client_key, exist_ok=True)

    log_lines: list[str] = []
    stage_placeholder = st.empty()
    log_placeholder = st.empty()
    current_stage = "Starting..."

    with st.status("Pipeline running...", expanded=True) as status:
        for line in _run_pipeline(run_args):
            if not line.strip():
                continue
            # Detect stage banners
            if line.strip().startswith("Stage") and "/" in line:
                current_stage = line.strip().strip("= ")
                stage_placeholder.markdown(f"**{current_stage}**")
            elif "===" in line:
                pass  # skip separator lines from display
            else:
                log_lines.append(line.strip())
                log_placeholder.code("\n".join(log_lines[-25:]), language=None)

        elapsed = time.time() - start_time
        status.update(
            label=f"✅ Done in {elapsed:.0f}s",
            state="complete",
            expanded=False,
        )

    # -----------------------------------------------------------------------
    # Output display
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Generated outputs")

    brief_path = _latest_output(client_key, "brief")
    article_path = _latest_output(client_key, "article")

    tab_article, tab_brief = st.tabs(["📄 Article", "📋 Brief"])

    with tab_article:
        if article_path:
            col_dl, col_info = st.columns([1, 4])
            with col_dl:
                _download_button(article_path, "⬇️ Download Article (.docx)")
            with col_info:
                st.caption(f"File: `{article_path.name}`")
            st.divider()
            st.markdown(_read_docx_for_display(article_path))
        else:
            st.warning("No article file found. Check the pipeline log above for errors.")

    with tab_brief:
        if brief_path:
            col_dl, col_info = st.columns([1, 4])
            with col_dl:
                _download_button(brief_path, "⬇️ Download Brief (.docx)")
            with col_info:
                st.caption(f"File: `{brief_path.name}`")
            st.divider()
            st.markdown(_read_docx_for_display(brief_path))
        else:
            st.warning("No brief file found. Check the pipeline log above for errors.")
