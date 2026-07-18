#!/usr/bin/env python3
"""
Wild_Root_Prompt — Hugging Face Space demo.

Browses the 173 prompt engineering techniques (same
prompt_expert_methodology.json used by the local CLI/web UI — single
source of truth, no data duplication) across 15 categories.

Deliberately has no Ollama dependency: a Space runs in HF's cloud and
cannot reach a user's local Ollama instance, so this is a read-only
catalog/reference, not a generator. Run the actual tool locally (see
the GitHub repo) for generation.
"""
import json
from pathlib import Path

import gradio as gr
import pandas as pd

DATA_FILE = Path(__file__).resolve().parent / "prompt_expert_methodology.json"
REPO_URL = "https://github.com/TFD-42/Wild_Root_Prompt"

with open(DATA_FILE, encoding="utf-8") as f:
    _data = json.load(f)

_rows = []
for category in _data["categories"]:
    for technique in category["techniques"]:
        _rows.append({
            "ID": technique["id"],
            "Category": category["name"],
            "Technique": technique["title"],
            "Description": technique["description"],
        })

FULL_DF = pd.DataFrame(_rows)
TOTAL_TECHNIQUES = len(FULL_DF)
CATEGORY_NAMES = ["All categories"] + [c["name"] for c in _data["categories"]]


def filter_techniques(category: str, query: str) -> pd.DataFrame:
    df = FULL_DF
    if category and category != "All categories":
        df = df[df["Category"] == category]
    if query and query.strip():
        q = query.strip().lower()
        mask = (
            df["Technique"].str.lower().str.contains(q)
            | df["Description"].str.lower().str.contains(q)
        )
        df = df[mask]
    return df


with gr.Blocks(title="Wild_Root_Prompt — Technique Browser") as demo:
    gr.Markdown(
        f"# 🌿 Wild_Root_Prompt — Prompt Engineering Technique Browser\n"
        f"**{TOTAL_TECHNIQUES} techniques** across **{len(_data['categories'])} categories** — "
        f"Chain-of-Thought, Tree-of-Thought, ReAct, MECE, red teaming, and more.\n\n"
        f"This is a read-only reference. The actual tool runs 100% locally via "
        f"[Ollama]({REPO_URL}) — no cloud API keys, nothing leaves your machine.\n"
        f"[View on GitHub]({REPO_URL}) · [Download / install]({REPO_URL}#quick-start)"
    )

    with gr.Row():
        category_dropdown = gr.Dropdown(
            choices=CATEGORY_NAMES, value="All categories", label="Category"
        )
        search_box = gr.Textbox(
            label="Search", placeholder="Search technique names or descriptions..."
        )

    table = gr.Dataframe(
        value=FULL_DF,
        headers=["ID", "Category", "Technique", "Description"],
        wrap=True,
        interactive=False,
    )

    category_dropdown.change(filter_techniques, [category_dropdown, search_box], table)
    search_box.change(filter_techniques, [category_dropdown, search_box], table)

if __name__ == "__main__":
    demo.launch()
