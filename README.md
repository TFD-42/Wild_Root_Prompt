# Pro-Prompt

**Reproducible instruction manifest generator powered by local LLMs via Ollama.**

Pro-Prompt generates structured, expert-level instruction manifests from task descriptions. It leverages 100 prompt engineering techniques to force exhaustive, high-quality outputs from any Ollama-compatible model --- no cloud API keys required.

---

## Features

- **Interactive launcher** --- numbered menu, no CLI flags to memorize
- **Model auto-detection** --- lists locally installed Ollama models with numbered picking
- **Auto-install** --- installs Ollama and Python automatically on macOS, Linux, and Windows
- **Auto-pull** --- downloads missing models on demand via `ollama pull`
- **Single model generation** with real-time streaming in terminal
- **Parallel dual-model generation** with split-screen display (two columns, live tokens)
- **Expert synthesis** --- merges two manifests into a unified, superior document
- **Full pipeline** --- parallel generation + synthesis in one command
- **100 prompt engineering techniques** from the methodology database, selectable per run
- **Web enrichment** --- automatic DuckDuckGo search to inject real-world context (when internet is available)
- **Session memory** --- tracks past runs for cross-session coherence
- **Persistent settings** --- models, techniques, temperature saved locally in `settings.json`

## Quick Start

### Install

**macOS / Linux:**

```bash
git clone https://github.com/TFD-42/Pro-Prompt.git
cd pro-prompt
chmod +x install.sh
./install.sh
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/TFD-42/Pro-Prompt.git
cd pro-prompt
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1
```

The installer handles everything: Ollama, Python 3, virtual environment, and dependencies.

### Run

```bash
source .venv/bin/activate    # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows

python3 prompt_expert_enhence.py
```

Launches the interactive menu. No arguments needed.

### CLI Mode

Pass arguments directly for scripting and automation:

```bash
python3 prompt_expert_enhence.py generate "Design a REST API" --model llama3:latest
python3 prompt_expert_enhence.py parallel "Design a REST API" --model-a llama3 --model-b qwen2.5:7b
python3 prompt_expert_enhence.py full "Design a REST API" --techniques "1-30"
```

## Interactive Menu

```
==============================================================
   MANIFEST GENERATOR  -  Prompt Expert Launcher
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

## Prompt Engineering Techniques

Pro-Prompt ships with **173 techniques** across **15 categories** in `prompte_expert_methodologie.json`, plus 8 anti-patterns and a quick-reference matrix for task-based selection.

**Categories:** Framing (zero/few/many-shot), Directed (CoT, ToT, GoT, ReAct, PoT), Depth-forcing, Constraint-based, Multi-perspective, Meta/recursive (self-critique, constitutional), Structural, Persona/role, Emergent (emotional priming, anchoring), Cognitive decomposition (MECE, first principles), Adversarial (red team, stress test), Hybrid multi-pass, Evidence/justification, Creative/narrative, Rarely-explored domains.

**Default set (15 techniques):** step-by-step, reframing, anti-lazy, recursive deepening, counter-arguments, examples, outline-then-expand, definition-first, first-principles, no-word-limit, Tree-of-Thought, constraint stacking, constitutional prompting, MECE decomposition, assumption mapping.

Select techniques per run:

```bash
# Specific IDs
--techniques "1,5,8,10,25"

# Range
--techniques "1-30"

# All 173
--techniques "1-173"

# List available (grouped by category)
python3 prompt_expert_enhence.py generate x --list-techniques
```

In the interactive menu, use option `6` to configure or option `7` to browse (now with category grouping).

## Web Enrichment

When internet is available, Pro-Prompt automatically searches DuckDuckGo for the task description, fetches top results, and injects relevant context into the prompt. This runs before generation and adds real-world grounding without any API keys.

Toggle via the advanced settings menu (option `8`) or `--no-web` flag.

## Output Structure

Generated manifests follow a 12-section structure:

1. Title & Executive Summary
2. Objective & Success Definition
3. Execution Context & Prerequisites
4. Ambiguity Zones
5. Step Decomposition (Detailed Pipeline)
6. Control Loops & Scoring
7. Persistent Artifacts
8. Constraints & Guardrails
9. Error Handling Strategy
10. Final Deliverable & Format
11. Reproducibility Checklist
12. Notes for the Target Agent

## Project Structure

```
pro-prompt/
  prompt_expert_enhence.py       # Main application (1600 lines)
  prompte_expert_methodologie.json  # 100 prompt engineering techniques
  requirements.txt               # Python dependencies (requests)
  install.sh                     # Installer for macOS/Linux
  install.ps1                    # Installer for Windows
  .gitignore
  README.md
  memory/                        # Session history (gitignored)
  outputs/                       # Generated manifests (gitignored)
```

## Requirements

- **Ollama** --- installed automatically by the installer, or manually from [ollama.com](https://ollama.com)
- **Python 3.8+** --- installed automatically by the installer
- **requests** --- installed via `pip install -r requirements.txt`
- At least one Ollama model pulled (the launcher handles this interactively)

## Configuration

All settings persist in `settings.json` (gitignored, local to each user):

| Setting | Default | Description |
|---------|---------|-------------|
| `model_a` | `llama3:latest` | Primary generation model |
| `model_b` | `qwen2.5:7b` | Secondary model for parallel runs |
| `synthesis_model` | `qwen2.5:7b` | Model used for synthesis |
| `temperature` | `0.3` | LLM temperature (0.0--1.0) |
| `timeout` | `600` | Seconds per Ollama call |
| `techniques` | `[1,5,8,10,12,14,18,25,40,47,108,121,125,147,153]` | Active technique IDs (from 173 available) |
| `use_web` | `true` | Enable web enrichment |
| `stream` | `true` | Enable real-time streaming |

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `python3 -m py_compile prompt_expert_enhence.py` before committing
4. Open a pull request

Keep `settings.json`, `outputs/`, and `memory/sessions.json` out of commits (they are gitignored).
