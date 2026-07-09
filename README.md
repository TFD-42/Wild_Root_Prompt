# Pro-Prompt — Local LLM Prompt Enhancement Tool v2.3

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-compatible-green.svg)](https://ollama.com)
[![Techniques](https://img.shields.io/badge/Techniques-173-orange.svg)](#prompt-engineering-techniques)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows%20%7C%20Android-lightgrey.svg)](#install)

**Transform any raw prompt into expert-level output using local LLMs via Ollama — no cloud API keys, no data sent to external servers.**

<img width="1983" height="793" alt="llm" src="https://github.com/user-attachments/assets/4623620d-df38-41ae-834e-3fa239f22e6f" />

Pro-Prompt enhances any prompt before it reaches your LLM. A **pre-processor** first restructures and clarifies your raw input, then applies **173 prompt engineering techniques** across 15 categories (Chain-of-Thought, Tree-of-Thought, ReAct, MECE, red teaming, and more) to generate exhaustive, high-quality outputs. Novice users get a **local web UI** (one click); power users get a full **CLI** with parallel dual-model generation, split-screen streaming, and expert synthesis.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Pre-processor** | Ollama restructures and completes your raw input before the main pipeline (toggleable) |
| **Local web UI** | One-click browser interface at `http://localhost:7860` — novice-friendly, no CLI needed |
| **Interactive CLI** | Numbered menu, no flags to memorize |
| **Two output modes** | **Quick**: single enhanced prompt ready to paste · **Full**: exhaustive 12-section manifest |
| **173 prompt engineering techniques** | Organized in 15 categories with anti-patterns and quick-reference matrix |
| **60 /slash metacommands** | Inline modifiers: persona, format, depth, reasoning, quality, context |
| **Single model generation** | Real-time token streaming in terminal or browser |
| **Parallel dual-model generation** | Split-screen display with two columns, live tokens |
| **Expert synthesis** | Merges two outputs into a unified, superior document with streaming |
| **Full pipeline** | Parallel generation + synthesis in one command |
| **Web enrichment** | Automatic DuckDuckGo search for real-world context (toggleable, SSRF-protected) |
| **Model auto-detection** | Lists locally installed Ollama models with numbered picker at each run |
| **First-run guidance** | If no models installed, offers guided pull with RAM requirements |
| **One-click launchers** | `Pro_Prompt.command` (macOS) · `Pro_Prompt.bat` (Windows) · `Pro_Prompt` (Linux) |
| **Cross-platform install** | `install.sh` (macOS/Linux) · `install.ps1` (Windows) · `install_termux.sh` (Android) |
| **Zero-trust security** | Input sanitization, SSRF block, no PII in logs, random session key |
| **Session memory** | Tracks past runs for cross-session coherence |
| **Persistent settings** | Models, techniques, temperature, output mode, pre-processor saved locally |

---

## Quick Start

### Install

**macOS / Linux:**

```bash
git clone https://github.com/TFD-42/Pro-Prompt.git
cd Pro-Prompt
chmod +x install.sh
./install.sh
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/TFD-42/Pro-Prompt.git
cd Pro-Prompt
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1
```

**Android / Termux:**

```bash
git clone https://github.com/TFD-42/Pro-Prompt.git
cd Pro-Prompt
chmod +x install_termux.sh
./install_termux.sh
```

The installer handles everything: Ollama, Python 3, virtual environment, and dependencies. It also creates a one-click launcher.

### Launch — Web UI (novice-friendly)

| Platform | Action |
|----------|--------|
| **macOS** | Double-click `Pro_Prompt.command` in Finder |
| **Windows** | Double-click `Pro_Prompt.bat` |
| **Linux** | Run `./Pro_Prompt` in terminal |
| **Any** | `python3 prompt_expert_enhance.py --web` |

Opens `http://localhost:7860` in your browser automatically.

### Launch — CLI (power users)

```bash
source .venv/bin/activate    # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows

python3 prompt_expert_enhance.py
```

Launches the interactive numbered menu. No arguments needed.

### CLI Mode

Pass arguments directly for scripting and automation:

```bash
# Single model generation
python3 prompt_expert_enhance.py generate "Design a REST API" --model llama3:latest

# Parallel dual-model generation
python3 prompt_expert_enhance.py parallel "Design a REST API" --model-a llama3 --model-b qwen2.5:7b

# Full pipeline (parallel + synthesis)
python3 prompt_expert_enhance.py full "Design a REST API" --techniques "1-30"

# List all 173 techniques grouped by category
python3 prompt_expert_enhance.py generate x --list-techniques
```

---

## Interactive Menu

```
==============================================================
   PRO-PROMPT  —  Expert Prompt Enhancement Tool  v2.2
==============================================================
   Model A     : llama3:latest
   Model B     : qwen2.5:7b
   Synthesis   : qwen2.5:7b
   Temperature : 0.3
   Techniques  : 15 active / 173 available
   Internet    : ON   Web enrichment : ON   Streaming : ON
--------------------------------------------------------------

  1.  Single generation         (1 model, streaming)
  2.  Parallel generation       (2 models, split screen)
  3.  Full pipeline             (parallel + synthesis)
  4.  Synthesize 2 files

  5.  Configure models
  6.  Configure techniques
  7.  Browse available techniques
  8.  Advanced settings          (temperature, timeout, url, web, stream)

  9.  View memory
  10. Clear memory

  0.  Quit
```

### Model Picker

When selecting a model, Pro-Prompt lists all locally installed models:

```
  -- Generation model --
  Locally installed models:
      1. llama3:latest                   4.7GB  2026-05-20  <-- current
      2. qwen2.5:7b                      4.4GB  2026-05-18
      3. dolphin3:latest                 4.6GB  2026-05-07
      4. [Enter a name manually / pull a new model]

  Choice [llama3:latest] >
```

Type a number to select, a model name to pull, or Enter to keep the current one.

---

## Prompt Engineering Techniques

Pro-Prompt ships with **173 techniques** across **15 categories** in `prompt_expert_methodology.json`, plus **8 anti-patterns** and a **quick-reference matrix** for task-based technique selection.

### Categories

| # | Category | Techniques | Examples |
|---|----------|-----------|----------|
| 1 | **Framing** | 6 | Zero-shot, few-shot, many-shot, negative-shot, contrastive prompting |
| 2 | **Directed reasoning** | 10 | Chain-of-Thought (CoT), Tree-of-Thought (ToT), Graph-of-Thought (GoT), ReAct, Program-of-Thought (PoT), Skeleton-of-Thought, least-to-most |
| 3 | **Depth forcing** | 11 | Output length specification, recursive deepening, exhaustive enumeration, anti-lazy preamble |
| 4 | **Constraint-based** | 21 | Format forcing, vocabulary constraint, register constraint, perspective constraint, inverse prompting, rubber duck, constraint stacking |
| 5 | **Multi-perspective** | 9 | Multi-viewpoint analysis, counter-arguments, audience layering, cross-disciplinary |
| 6 | **Meta / recursive** | 15 | Self-critique, self-refine, self-ask, meta-prompting, constitutional prompting, recursive summarization |
| 7 | **Structural** | 13 | Instruction decomposition, strong delimiters, priority stacking, prompt chaining, conditional prompting |
| 8 | **Persona & role** | 9 | Expert persona, multi-persona debate, naive persona, devil's advocate, future historian |
| 9 | **Emergent** | 14 | Emotional priming, anchoring, semantic pressure, cognitive load offloading, counterfactual, steelmanning, pre-mortem |
| 10 | **Cognitive decomposition** | 9 | MECE, first principles, five whys, abstraction ladder, dual process, Socratic decomposition, ontology extraction |
| 11 | **Adversarial** | 9 | Red teaming, stress testing, bias hunting, assumption mapping |
| 12 | **Hybrid multi-pass** | 8 | Generate-then-filter, breadth-first/depth-first, adversarial refinement loop, perspective rotation, zoom protocol |
| 13 | **Evidence & justification** | 16 | Citation thresholds, uncertainty quantification, historical grounding, tiered evidence |
| 14 | **Creative & narrative** | 8 | Analogy generation, narrative embedding, timeline construction, forced self-interruption |
| 15 | **Rarely explored** | 15 | Formal logic coherence, invariant detection, test generation, tacit knowledge elicitation, weak signal detection, second-order effects, heuristic generation |

### Default Set (15 techniques)

Step-by-step reasoning, forced reframing, anti-lazy preamble, recursive deepening, counter-arguments, example-driven expansion, outline-then-expand, definition-first, first-principles, no-word-limit, Tree-of-Thought, constraint stacking, constitutional prompting, MECE decomposition, assumption mapping.

### Selecting Techniques

```bash
--techniques "1,5,8,10,25"     # Specific IDs
--techniques "1-30"             # Range
--techniques "1-173"            # All 173 techniques
```

In the interactive menu, use option `6` to configure or option `7` to browse (grouped by category with anti-patterns and quick reference).

---

## Web Enrichment

When internet is available, Pro-Prompt automatically searches DuckDuckGo for the task description, fetches top results, and injects relevant context into the prompt. This runs before generation and adds real-world grounding without any API keys.

Toggle via the advanced settings menu (option `8`) or `--no-web` flag.

---

## Output Structure

Generated manifests follow a **12-section structure**:

1. Title & Executive Summary
2. Final Objective & Success Definition
3. Execution Context & Prerequisites
4. Ambiguity Zones to Resolve
5. Step Decomposition (Detailed Pipeline)
6. Control Loops & Scoring
7. Persistent Artifacts to Maintain
8. Constraints & Guardrails
9. Error Handling Strategy
10. Final Deliverable & Output Format
11. Reproducibility Checklist
12. Notes for the Target Agent

---

## Project Structure

```
Pro-Prompt/
  prompt_expert_enhance.py        # Main application — CLI + pre-processor (~2200 lines)
  web_server.py                   # Local web UI server (Flask, SSE streaming)
  prompt_expert_methodology.json  # 173 prompt engineering techniques (15 categories)
  requirements.txt                # Python deps: requests, flask
  install.sh                      # Installer — macOS / Linux
  install.ps1                     # Installer — Windows
  install_termux.sh               # Installer — Android / Termux
  Pro_Prompt.command              # macOS double-click launcher (web UI)
  Pro_Prompt.bat                  # Windows launcher (created by install.ps1)
  Pro_Prompt                      # Linux/macOS terminal launcher (created by install.sh)
  tools/
    privacy_scan.py               # PII scanner — run before every push
  build_tools/                    # Implementation specs (reference docs)
  .gitignore
  README.md
  LICENSE
  memory/                         # Session history (gitignored)
  outputs/                        # Generated outputs (gitignored)
```

## Requirements

- **[Ollama](https://ollama.com)** — installed automatically by the installer
- **Python 3.8+** — installed automatically by the installer
- **requests** — installed via `pip install -r requirements.txt`
- At least one Ollama model pulled (the launcher handles this interactively)

## Configuration

All settings persist in `settings.json` (gitignored, local to each user):

| Setting | Default | Description |
|---------|---------|-------------|
| `model_a` | `llama3:latest` | Primary generation model |
| `model_b` | `qwen2.5:7b` | Secondary model for parallel runs |
| `synthesis_model` | `qwen2.5:7b` | Model used for expert synthesis |
| `temperature` | `0.3` | LLM temperature (0.0–1.0) |
| `timeout` | `600` | Seconds per Ollama call |
| `techniques` | `[1,5,8,10,12,14,18,25,40,47,108,121,125,147,153]` | Active technique IDs (from 173 available) |
| `use_web` | `true` | Enable web enrichment (DuckDuckGo, SSRF-protected) |
| `stream` | `true` | Enable real-time streaming |
| `output_mode` | `"full"` | `"quick"` = enhanced prompt · `"full"` = 12-section manifest |
| `use_pre_processor` | `true` | Enable pre-processor step (Ollama restructures raw input) |
| `pre_processor_model` | `""` | Model for pre-processor (`""` = use Model A) |

## How It Works

1. **You describe a task** — in natural language, as simple or complex as you want
2. **Pro-Prompt builds an expert prompt** — injecting selected techniques, web context, and session memory
3. **Local LLM generates a manifest** — a structured 12-section document describing the task with methodological precision
4. **Optionally, two models generate in parallel** — and a synthesis pass merges them into a superior unified document
5. **The output is a reproducible instruction set** — ready to be executed by any LLM agent (Claude, GPT, Gemini, Llama, Mistral, Qwen)

## Use Cases

- **Prompt engineering** — Generate expert-level prompts for any LLM task
- **Task specification** — Create detailed, unambiguous task descriptions for AI agents
- **Knowledge extraction** — Force exhaustive exploration of any topic
- **Comparative analysis** — Run two models in parallel and synthesize the best of both
- **Reproducible AI workflows** — Manifests can be reused across models and platforms
- **Learning prompt engineering** — Browse 173 techniques with descriptions and categories

## License

[MIT](LICENSE)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `python3 -m py_compile prompt_expert_enhance.py` before committing
4. Open a pull request

Keep `settings.json`, `outputs/`, and `memory/sessions.json` out of commits (they are gitignored).
