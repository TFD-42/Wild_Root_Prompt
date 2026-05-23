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
git clone https://github.com/<your-org>/pro-prompt.git
cd pro-prompt
chmod +x install.sh
./install.sh
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/<your-org>/pro-prompt.git
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
   Synthese    : qwen2.5:7b
   Temperature : 0.3
   Techniques  : 10 actives
   Internet    : ON   Web enrichment : ON   Streaming : ON
--------------------------------------------------------------

  1.  Generation simple        (1 model, streaming)
  2.  Generation parallele      (2 models, split screen)
  3.  Pipeline complet          (parallel + synthesis)
  4.  Synthese de 2 fichiers

  5.  Configurer les modeles
  6.  Configurer les techniques
  7.  Voir les techniques disponibles
  8.  Parametres avances        (temperature, timeout, url, web, stream)

  9.  Voir la memoire
  10. Effacer la memoire

  0.  Quitter
```

### Model Picker

When selecting a model, Pro-Prompt lists all locally installed models:

```
  -- Modele de generation --
  Modeles installes localement :
      1. llama3:latest                   4.7GB  2026-05-20  <-- actuel
      2. qwen2.5:7b                      4.4GB  2026-05-18
      3. dolphin3:latest                 4.6GB  2026-05-07
      4. [Entrer un nom manuellement / pull un nouveau modele]

  Choix [llama3:latest] >
```

Type a number to select, a model name to pull, or Enter to keep the current one.

## Prompt Engineering Techniques

Pro-Prompt ships with 100 techniques in `prompte_expert_methodologie.json`. Each technique forces the LLM into deeper, more structured output.

**Default set (10 techniques):** step-by-step reasoning, forced reframing, anti-lazy preamble, recursive deepening, counter-arguments, example-driven expansion, outline-then-expand, definition-first, first-principles, no-word-limit.

Select techniques per run:

```bash
# Specific IDs
--techniques "1,5,8,10,25"

# Range
--techniques "1-30"

# All 100
--techniques "1-100"

# List available
python3 prompt_expert_enhence.py generate x --list-techniques
```

In the interactive menu, use option `6` to configure or option `7` to browse.

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
| `techniques` | `[1,5,8,10,12,14,18,25,40,47]` | Active technique IDs |
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
