#!/usr/bin/env python3
"""
Pro-Prompt – Expert Prompt Enhancement Tool powered by Ollama.

Version: 2.2.0

Two output modes:
    quick  — single enhanced prompt, ready to paste into any LLM
    full   — exhaustive 12-section instruction manifest (expert use)

Usage:
    python prompt_expert_enhance.py                    (interactive menu)
    python prompt_expert_enhance.py generate <task> [options]
    python prompt_expert_enhance.py parallel <task> [options]
    python prompt_expert_enhance.py synthesis <task> <file_a> <file_b> [options]
    python prompt_expert_enhance.py full <task> [options]
    python prompt_expert_enhance.py memory view
    python prompt_expert_enhance.py memory clear

Metacommands — prefix your task with /slash modifiers:
    /expert /humain /enfant /sceptique /mentor /cynique /serieux /humour
    /tableau /json /markdown /points /checklist
    /resume /concis /detaille /limite:N
    /etapes /exemple /analogie /pourcontre /debat /reverse /iterer /ameliorer
    /precision /hypotheses /sources /risques /decision /verification /audit
    /raisonnement /minimal /silence /urgent /questionner /historique /futuriste
    /niveau:debutant|intermediaire|expert   /confiance   /comparatif

Commands:
    generate       Single model manifest generation (multi‑topic optional).
    parallel       Parallel generation from two models (MODEL_A, MODEL_B).
    synthesis      Run the meta‑architect synthesis on two existing manifests.
    full           Full pipeline: parallel + synthesis.
    memory         Manage session memory (view / clear).

For detailed help on a command: manifest <command> --help
"""

import argparse
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from urllib.parse import quote_plus

import requests

# ----------------------------------------------------------------------
# Configuration – can be overridden via environment or command line
# ----------------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"
OUTPUT_DIR = BASE_DIR / "outputs"
MEMORY_FILE = MEMORY_DIR / "sessions.json"
METHODOLOGY_FILE = BASE_DIR / "prompt_expert_methodology.json"
DEFAULT_MODEL_A = "llama3:latest"
DEFAULT_MODEL_B = "qwen2.5:7b"
DEFAULT_SYNTH_MODEL = "qwen2.5:7b"
DEFAULT_TEMPERATURE = 0.3

# Generic, non-identifying HTTP User-Agent for web enrichment requests.
# Change this string if you want to identify the tool differently,
# but never include real OS, device, or browser version info here.
HTTP_USER_AGENT = "Mozilla/5.0 (compatible; ManifestGen/2.1; +https://github.com/TFD-42/Pro-Prompt)"
DEFAULT_TIMEOUT = 600  # seconds for a single Ollama call
SYNTH_TIMEOUT = 1200   # longer timeout for synthesis

# Default techniques applied when none are specified (configurable via CLI or settings)
DEFAULT_TECHNIQUES = [1, 5, 8, 10, 12, 14, 18, 25, 40, 47, 108, 121, 125, 147, 153]

# Create directories at import time
MEMORY_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Load methodologies from JSON
TECHNIQUES_DB: Dict[int, Dict[str, str]] = {}
CATEGORIES_DB: List[Dict] = []
ANTI_PATTERNS: List[Dict] = []
QUICK_REFERENCE: Dict[str, List[int]] = {}

def load_methodologies():
    global TECHNIQUES_DB, CATEGORIES_DB, ANTI_PATTERNS, QUICK_REFERENCE
    if not METHODOLOGY_FILE.exists():
        return
    try:
        raw = METHODOLOGY_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if "categories" in data:
            CATEGORIES_DB = data["categories"]
            for cat in CATEGORIES_DB:
                for tech in cat.get("techniques", []):
                    TECHNIQUES_DB[tech["id"]] = {
                        "title": tech["title"],
                        "description": tech["description"],
                        "category": cat["name"],
                    }
            ANTI_PATTERNS = data.get("anti_patterns", [])
            QUICK_REFERENCE = data.get("quick_reference", {}).get("mappings", {})
        else:
            for line in raw.strip().split("\n"):
                if line and line[0].isdigit():
                    match = re.match(r"(\d+)\.\s+\*\*(.+?)\*\*\s+–\s+(.+)", line)
                    if match:
                        num = int(match.group(1))
                        TECHNIQUES_DB[num] = {"title": match.group(2), "description": match.group(3)}
    except Exception as e:
        logger.warning(f"Could not load methodologies: {e}")

load_methodologies()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("manifest_gen")


# ----------------------------------------------------------------------
# Ollama bootstrap — detect, install, list models, pull
# ----------------------------------------------------------------------
OLLAMA_API_BASE = OLLAMA_URL.rsplit("/api/", 1)[0]  # http://localhost:11434


def detect_os() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "mac"
    if s == "windows":
        return "windows"
    return "linux"


def is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def is_ollama_running() -> bool:
    try:
        requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def install_ollama_interactive() -> bool:
    os_type = detect_os()
    print()
    print("  [!] Ollama is not installed on this machine.")
    print(f"  Detected OS: {os_type}")
    print()
    if os_type == "mac":
        print("  Installation options:")
        print("    1. Automatic curl install (recommended)")
        print("    2. Cancel")
        c = input("  Choice > ").strip()
        if c != "1":
            return False
        print("\n  Installing ...")
        try:
            subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                check=True,
            )
            print("  Ollama installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] Installation failed: {e}")
            return False
    elif os_type == "linux":
        print("  Installation options:")
        print("    1. Automatic curl install (recommended)")
        print("    2. Cancel")
        c = input("  Choice > ").strip()
        if c != "1":
            return False
        print("\n  Installing ...")
        try:
            subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                check=True,
            )
            print("  Ollama installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] Installation failed: {e}")
            return False
    elif os_type == "windows":
        print("  Windows automatic installation:")
        print("    1. Download and run installer (winget)")
        print("    2. Cancel")
        c = input("  Choice > ").strip()
        if c != "1":
            return False
        print("\n  Installing via winget ...")
        try:
            subprocess.run(
                ["winget", "install", "Ollama.Ollama", "--accept-source-agreements", "--accept-package-agreements"],
                check=True,
            )
            print("  Ollama installed successfully.")
            print("  [!] Terminal restart may be required.")
            return True
        except FileNotFoundError:
            print("  [!] winget not available. Trying PowerShell fallback ...")
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '$env:TEMP\\OllamaSetup.exe'; Start-Process '$env:TEMP\\OllamaSetup.exe' -Wait"],
                    check=True,
                )
                print("  Installer launched. Wait for installation to complete.")
                return True
            except Exception as e2:
                print(f"  [ERROR] {e2}")
                print("  Install manually: https://ollama.com/download")
                return False
        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] {e}")
            return False
    return False


def start_ollama_serve():
    if is_ollama_running():
        return
    print("  Starting Ollama in background ...")
    os_type = detect_os()
    try:
        if os_type == "windows":
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        for _ in range(15):
            time.sleep(1)
            if is_ollama_running():
                print("  Ollama is ready.")
                return
        print("  [!] Ollama started but not ready yet. Continuing anyway.")
    except Exception as e:
        print(f"  [!] Could not start Ollama: {e}")


def list_local_models() -> List[Dict[str, str]]:
    try:
        resp = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = []
        for m in data.get("models", []):
            name = m.get("name", "")
            size_bytes = m.get("size", 0)
            size_gb = size_bytes / (1024 ** 3) if size_bytes else 0
            modified = m.get("modified_at", "")[:10]
            models.append({
                "name": name,
                "size": f"{size_gb:.1f}GB" if size_gb else "?",
                "modified": modified,
            })
        return models
    except Exception:
        return []


def pull_model_interactive(model_name: str) -> bool:
    print(f"\n  Downloading model '{model_name}' ...")
    print("  (This may take several minutes depending on size)")
    print()
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.strip()
            if line:
                sys.stdout.write(f"\r  {line[:70]:<70}")
                sys.stdout.flush()
        proc.wait()
        print()
        if proc.returncode == 0:
            print(f"  Model '{model_name}' downloaded successfully.")
            return True
        else:
            print(f"  [ERROR] ollama pull returned code {proc.returncode}")
            return False
    except FileNotFoundError:
        print("  [ERROR] 'ollama' command not found.")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def pick_model_interactive(label: str, current: str) -> str:
    models = list_local_models()
    print()
    if models:
        print(f"  -- {label} --")
        print(f"  Locally installed models:")
        for i, m in enumerate(models, 1):
            marker = " <-- current" if m["name"] == current else ""
            print(f"    {i:3d}. {m['name']:<30s}  {m['size']:>6s}  {m['modified']}{marker}")
        print(f"    {len(models)+1:3d}. [Enter a name manually / pull a new model]")
        print()
        raw = input(f"  Choice [{current}] > ").strip()
        if not raw:
            return current
        try:
            idx = int(raw)
            if 1 <= idx <= len(models):
                return models[idx - 1]["name"]
        except ValueError:
            pass
        if raw.isdigit() and int(raw) == len(models) + 1:
            raw = ""
    else:
        print(f"  -- {label} --")
        print("  No models installed locally.")
        print()
        raw = ""

    if not raw:
        name = input(f"  Model name (e.g. llama3:latest, qwen2.5:7b) [{current}] > ").strip()
        if not name:
            return current
        raw = name

    local_names = [m["name"] for m in models]
    if raw not in local_names:
        print(f"\n  Model '{raw}' is not installed locally.")
        do_pull = input("  Download now? (yes/no) [yes] > ").strip().lower()
        if do_pull in ("", "yes", "y", "oui", "o", "1"):
            if pull_model_interactive(raw):
                return raw
            else:
                print(f"  Using previous model: {current}")
                return current
        else:
            print(f"  [!] Model '{raw}' will be used as-is (may fail if not available).")
    return raw


def ensure_ollama_ready():
    if not is_ollama_installed():
        if not install_ollama_interactive():
            print("\n  [!] Ollama is not available. Generation will fail.")
            print("  Install manually: https://ollama.com/download")
            return
    if not is_ollama_running():
        start_ollama_serve()


def ensure_models_available(settings: dict):
    """First-run: if no models are installed, guide the user to pull one."""
    models = list_local_models()
    if models:
        return
    print()
    print("  " + "─" * 58)
    print("  No local models found. You need at least one to generate.")
    print()
    print("  Recommended models (pick based on available RAM):")
    print("    1.  llama3.2:3b    ~2 GB   — fast, lightweight, good quality")
    print("    2.  llama3:8b      ~4.7 GB — solid all-rounder  (recommended)")
    print("    3.  qwen2.5:7b     ~4.4 GB — strong reasoning")
    print("    4.  mistral:7b     ~4.1 GB — instruction-tuned")
    print("    5.  Skip for now   (generation will fail until a model is pulled)")
    print("  " + "─" * 58)
    choice = input("  Choice [2] > ").strip() or "2"
    model_map = {
        "1": "llama3.2:3b",
        "2": "llama3:8b",
        "3": "qwen2.5:7b",
        "4": "mistral:7b",
    }
    if choice in model_map:
        chosen = model_map[choice]
        if pull_model_interactive(chosen):
            settings["model_a"] = chosen
            settings["model_b"] = chosen
            settings["synthesis_model"] = chosen
            save_settings(settings)
            print(f"\n  Default model set to: {chosen}")


# ----------------------------------------------------------------------
# Meta‑prompts (unchanged from original, kept for brevity)
# ----------------------------------------------------------------------
META_PROMPT = """
# META-PROMPT: REPRODUCIBLE INSTRUCTION MANIFEST GENERATOR

> Usage: Paste this meta-prompt into any LLM agent, then provide your task in the USER_INPUT section. It will produce a complete, expert-level instruction manifest that another LLM agent can execute without prior context.

---

## ROLE

You are a senior prompt architect specializing in producing reproducible instruction manifests. Your mission is never to write code or execute the task. Your mission is to produce a manifest document that describes the task with such methodological precision that another LLM agent (Claude, GPT, Gemini, Llama, Mistral, Qwen) can reproduce it entirely using its own implementation methods.

You write like an RFC author, product spec writer, or technical article author — not like a developer. You describe the WHAT, the WHY, the IN WHAT ORDER, and the CONCEPTUAL-HOW — never the SYNTACTIC-HOW.

---

## USER INPUT

<<<USER_INPUT
{USER_INPUT}
USER_INPUT>>>

{TOPIC_FOCUS}

{MEMORY_CONTEXT}

{WEB_CONTEXT}

---

## ABSOLUTE OUTPUT RULES

1. Zero lines of code. No code blocks. No raw shell commands. No API syntax.
2. Total reproducibility. A different LLM agent must be able to reproduce the result.
3. Implementation-agnostic.
4. Manifest / article / spec style. Numbered sections, clear headings.
5. Expert level. Anticipate edge cases, pitfalls, and ambiguities.
6. Self-diagnose ambiguity if the input is ambiguous.
7. No length limit: write as much as necessary to exhaust the subject.

---

## MANDATORY STRUCTURE OF THE GENERATED MANIFEST

You produce exactly the following 12 sections, in this order:

### § 1. TITLE & EXECUTIVE SUMMARY
### § 2. FINAL OBJECTIVE & SUCCESS DEFINITION
### § 3. EXECUTION CONTEXT & PREREQUISITES
### § 4. AMBIGUITY ZONES TO RESOLVE
### § 5. STEP DECOMPOSITION (DETAILED PIPELINE)
### § 6. CONTROL LOOPS & SCORING
### § 7. PERSISTENT ARTIFACTS TO MAINTAIN
### § 8. CONSTRAINTS & GUARDRAILS
### § 9. ERROR HANDLING STRATEGY
### § 10. FINAL DELIVERABLE & OUTPUT FORMAT
### § 11. REPRODUCIBILITY CHECKLIST
### § 12. NOTES FOR THE TARGET AGENT

---

## STRICT PROHIBITIONS

- No code blocks, regardless of justification.
- No shell commands, SQL queries, or raw API calls.
- No TODOs or "to be completed".
- No mention of yourself as the generator.
- No decorative emojis. Accepted symbols: empty square for checklists, arrow for transitions, § for sections.

---

Only produce the final manifest. No preamble. No conclusion. The manifest starts directly with "## § 1. TITLE & EXECUTIVE SUMMARY".
"""

SYNTH_PROMPT = """
# ROLE
You are a META-ARCHITECT of prompts, senior expert in LLM/AI/AGI instruction engineering, tasked with producing a FINAL SYNTHESIS with no length limit.

# MISSION
You have two instruction manifests generated by two distinct models (MODEL A and MODEL B) on the same user task. You must:

1. COMPARATIVE ANALYSIS: review both manifests, identify convergence points, divergences, omissions, and respective strengths and weaknesses.
2. MASTER PLAN: produce a structured, exhaustive, prioritized global plan.
3. UNIFIED SYNTHESIS: merge and enrich both manifests into a master document superior to either one, keeping the best of each, filling gaps, and adding blind spots that neither one saw.
4. FINAL EXPERT PROMPT-INSTRUCTION: at the end, produce a professional-quality expert prompt-instruction, ready to be injected as-is into another LLM agent (Claude, GPT, Gemini, etc.) to execute the task at the highest level.

# RULES
- No length limit: write as much as necessary, be exhaustive.
- No decorative unicode emojis.
- No executable code blocks.
- Style: technical, dense, professional, AGI prompt engineer expert level.
- Mandatory structure (numbered sections below).

# MANDATORY OUTPUT STRUCTURE

## PART I - COMPARATIVE ANALYSIS
### I.1 Convergences between the two manifests
### I.2 Notable divergences
### I.3 Detected omissions and blind spots
### I.4 Qualitative score by section (table)

## PART II - UNIFIED MASTER PLAN
### II.1 Vision and strategic objectives
### II.2 Major phases
### II.3 Dependencies and sequencing
### II.4 Critical risks and mitigation

## PART III - ENRICHED SYNTHETIC MANIFEST
Covers the 12 standard sections (§ 1 to § 12) in a unified, enriched version superior to both inputs.

## PART IV - FINAL EXPERT PROMPT-INSTRUCTION
A turnkey, self-contained prompt requiring no external context, ready to be pasted into any LLM agent to solve the task. Senior prompt engineer level. Include: role, context, constraints, methodology, success criteria, self-verification loops, deliverable format.

## PART V - META NOTES
Strategic advice for the target agent, known pitfalls, possible optimizations.

# INPUTS

## ORIGINAL USER TASK
<<<TASK
{USER_INPUT}
TASK>>>

## MODEL A MANIFEST ({MODEL_A})
<<<MANIFEST_A
{MANIFEST_A}
MANIFEST_A>>>

## MODEL B MANIFEST ({MODEL_B})
<<<MANIFEST_B
{MANIFEST_B}
MANIFEST_B>>>

{MEMORY_CONTEXT}

# START THE SYNTHESIS NOW
Begin directly with "## PART I - COMPARATIVE ANALYSIS". No preamble.
"""

QUICK_PROMPT = """
You are an expert prompt engineer with deep knowledge of LLM behavior.

Your task: take the user's raw input and rewrite it as a single, polished, production-ready prompt — optimized for maximum clarity, specificity, and LLM effectiveness.

Apply these prompt engineering techniques as you rewrite:
{TECHNIQUE_BLOCK}

{METACOMMANDS}

{TOPIC_FOCUS}

{MEMORY_CONTEXT}

{WEB_CONTEXT}

Raw user input:
<<<INPUT
{USER_INPUT}
INPUT>>>

Rules:
- Output ONLY the enhanced prompt. Nothing else.
- No preamble, no explanation, no meta-commentary, no section headers.
- The output must be ready to paste directly into any LLM (Claude, GPT, Gemini, Llama, Mistral).
- If the input contains /slash metacommands, they must be reflected in the style and tone of the enhanced prompt, not repeated literally.
- Be specific, concrete, and assume nothing the original left vague.

Start the enhanced prompt now:
"""

# ----------------------------------------------------------------------
# Persistent memory helpers (thread-safe with lock)
# ----------------------------------------------------------------------
_memory_lock = threading.Lock()

def load_memory() -> dict:
    with _memory_lock:
        if not MEMORY_FILE.exists():
            return {"sessions": []}
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Corrupted memory file; resetting.")
            return {"sessions": []}


def save_memory(mem: dict) -> None:
    with _memory_lock:
        MEMORY_FILE.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")


def append_session(entry: dict) -> None:
    mem = load_memory()
    mem.setdefault("sessions", []).append(entry)
    # keep only last 50 sessions
    mem["sessions"] = mem["sessions"][-50:]
    save_memory(mem)


def build_memory_context(max_items: int = 3) -> str:
    mem = load_memory()
    sessions = mem.get("sessions", [])[-max_items:]
    if not sessions:
        return ""
    lines = ["## MEMORY CONTEXT (previous sessions, for coherence)"]
    for s in sessions:
        lines.append(f"- [{s.get('timestamp','?')}] Task: {s.get('user_input','')[:200]}")
        if s.get("topics"):
            lines.append(f"  Topics covered: {', '.join(s['topics'])}")
    return "\n".join(lines)


def clear_memory():
    save_memory({"sessions": []})
    logger.info("Memory cleared.")


def view_memory() -> str:
    mem = load_memory()
    sessions = mem.get("sessions", [])
    if not sessions:
        return "No sessions in memory."
    out = [f"Total sessions: {len(sessions)}", ""]
    for i, s in enumerate(reversed(sessions), 1):
        out.append(f"### Session {i} - {s.get('timestamp','?')}")
        out.append(f"Task: {s.get('user_input','')[:300]}")
        if s.get("topics"):
            out.append(f"Topics: {', '.join(s['topics'])}")
        if s.get("files"):
            out.append(f"Files: {', '.join(s['files'])}")
        out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------
# Internet detection & web research
# ----------------------------------------------------------------------
_internet_available: Optional[bool] = None


def check_internet(timeout: float = 3.0) -> bool:
    global _internet_available
    if _internet_available is not None:
        return _internet_available
    for url in ("https://duckduckgo.com/", "https://www.google.com/"):
        try:
            requests.head(url, timeout=timeout, allow_redirects=True)
            _internet_available = True
            return True
        except Exception:
            continue
    _internet_available = False
    return False


def web_search_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": HTTP_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = []
        for m in re.finditer(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>',
            resp.text,
        ):
            href = m.group(1)
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if href and title:
                results.append({"title": title, "url": href})
            if len(results) >= max_results:
                break
        snippets = re.findall(
            r'<a class="result__snippet"[^>]*>(.*?)</a>', resp.text
        )
        for i, snip in enumerate(snippets):
            if i < len(results):
                results[i]["snippet"] = re.sub(r"<[^>]+>", "", snip).strip()
        return results
    except Exception as e:
        logger.debug(f"DuckDuckGo search failed: {e}")
        return []


def fetch_page_text(url: str, max_chars: int = 3000) -> str:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": HTTP_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        text = re.sub(r"<script[^>]*>.*?</script>", "", resp.text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def build_web_context(task: str, topic: str = "", max_results: int = 3, max_pages: int = 2) -> str:
    if not check_internet():
        return ""
    query = task
    if topic:
        query = f"{topic} {task}"
    logger.info(f"Web research: \"{query[:60]}\" ...")
    results = web_search_duckduckgo(query, max_results=max_results)
    if not results:
        logger.info("No web results found.")
        return ""
    lines = ["## WEB CONTEXT (automatic search, for enrichment)"]
    pages_fetched = 0
    for r in results:
        lines.append(f"- [{r['title']}]({r.get('url', '')})")
        if r.get("snippet"):
            lines.append(f"  Summary: {r['snippet']}")
        if pages_fetched < max_pages and r.get("url"):
            page_text = fetch_page_text(r["url"])
            if page_text:
                lines.append(f"  Excerpt: {page_text[:800]}")
                pages_fetched += 1
    logger.info(f"Web context: {len(results)} results, {pages_fetched} pages fetched.")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Ollama interaction — batch and streaming
# ----------------------------------------------------------------------
def query_ollama(
    model: str,
    prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
    num_predict: int = -1,
    timeout: int = DEFAULT_TIMEOUT,
    ollama_url: str = OLLAMA_URL,
    num_ctx: int = 8192,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    }
    try:
        resp = requests.post(ollama_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "[Empty response]")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not connect to Ollama at {ollama_url}. Is it running?")
    except requests.exceptions.Timeout:
        raise TimeoutError(f"Timeout while waiting for model {model}.")
    except Exception as e:
        raise RuntimeError(f"Ollama call to {model} failed: {e}")


def query_ollama_stream(
    model: str,
    prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
    num_predict: int = -1,
    timeout: int = DEFAULT_TIMEOUT,
    ollama_url: str = OLLAMA_URL,
    callback=None,
    num_ctx: int = 8192,
):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    }
    full_text = []
    try:
        with requests.post(ollama_url, json=payload, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                chunk = json.loads(raw_line)
                token = chunk.get("response", "")
                if token:
                    full_text.append(token)
                    if callback:
                        callback(token)
                if chunk.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not connect to Ollama at {ollama_url}. Is it running?")
    except requests.exceptions.Timeout:
        raise TimeoutError(f"Timeout while waiting for model {model}.")
    except Exception as e:
        raise RuntimeError(f"Ollama stream to {model} failed: {e}")
    return "".join(full_text)


# ----------------------------------------------------------------------
# Dual-pane streaming for parallel generation
# ----------------------------------------------------------------------
class DualPaneDisplay:
    def __init__(self, label_a: str, label_b: str):
        self._lock = threading.Lock()
        self.label_a = label_a
        self.label_b = label_b
        self.buf_a: List[str] = []
        self.buf_b: List[str] = []
        self.lines_a: List[str] = [""]
        self.lines_b: List[str] = [""]
        term_size = shutil.get_terminal_size((120, 40))
        self.width = term_size.columns
        self.height = term_size.lines - 4
        self.col_w = (self.width - 3) // 2
        self._last_drawn = 0

    def _tokenize_lines(self, buf: List[str]) -> List[str]:
        text = "".join(buf)
        raw_lines = text.split("\n")
        wrapped = []
        for rl in raw_lines:
            while len(rl) > self.col_w:
                wrapped.append(rl[: self.col_w])
                rl = rl[self.col_w :]
            wrapped.append(rl)
        return wrapped

    def feed_a(self, token: str):
        with self._lock:
            self.buf_a.append(token)
            self.lines_a = self._tokenize_lines(self.buf_a)
        self._draw()

    def feed_b(self, token: str):
        with self._lock:
            self.buf_b.append(token)
            self.lines_b = self._tokenize_lines(self.buf_b)
        self._draw()

    def _draw(self):
        with self._lock:
            visible = self.height - 2
            la = self.lines_a[-visible:] if len(self.lines_a) > visible else self.lines_a
            lb = self.lines_b[-visible:] if len(self.lines_b) > visible else self.lines_b
            max_rows = max(len(la), len(lb), 1)

            header_a = f" {self.label_a} "
            header_b = f" {self.label_b} "
            ha = header_a.center(self.col_w, "-")
            hb = header_b.center(self.col_w, "-")

            output = [f"\033[2J\033[H{ha} | {hb}"]
            for i in range(max_rows):
                left = la[i] if i < len(la) else ""
                right = lb[i] if i < len(lb) else ""
                left = left[: self.col_w].ljust(self.col_w)
                right = right[: self.col_w].ljust(self.col_w)
                output.append(f"{left} | {right}")
            sep = "-" * self.col_w + "-+-" + "-" * self.col_w
            output.append(sep)
            status = f"  A: {len(self.lines_a)} lines | B: {len(self.lines_b)} lines"
            output.append(status)

            sys.stdout.write("\n".join(output))
            sys.stdout.flush()

    def get_texts(self) -> Tuple[str, str]:
        return "".join(self.buf_a), "".join(self.buf_b)


def get_technique_boost(technique_ids: List[int]) -> str:
    """Generate prompt enhancement block from selected techniques, grouped by category."""
    if not technique_ids:
        return ""
    by_cat: Dict[str, List[str]] = {}
    for tid in sorted(technique_ids):
        if tid in TECHNIQUES_DB:
            tech = TECHNIQUES_DB[tid]
            cat = tech.get("category", "Other")
            by_cat.setdefault(cat, []).append(f"- {tech['title']}: {tech['description']}")
    if not by_cat:
        return ""
    blocks = []
    for cat_name, items in by_cat.items():
        blocks.append(f"### {cat_name}")
        blocks.extend(items)
    blocks_str = "\n".join(blocks)
    if not blocks_str:
        return ""
    return (
        "## PROMPT ENGINEERING TECHNIQUES TO APPLY\n"
        "Integrate the following methods into your generation for superior quality:\n"
        + blocks_str
    )


def build_full_prompt(
    user_input: str,
    topic: str = "",
    use_memory: bool = True,
    techniques: Optional[List[int]] = None,
    use_web: bool = True,
    mode: str = "full",
) -> str:
    # Extract /slash metacommands from the raw input
    clean_input, meta_block = parse_metacommands(user_input)

    topic_block = ""
    if topic.strip():
        if mode == "quick":
            topic_block = f"## FOCUS\nConcentrate the enhanced prompt on this specific angle: '{topic.strip()}'."
        else:
            topic_block = (
                "## FOCUS TOPIC\n"
                f"Focus this entire manifest on the following topic: '{topic.strip()}'. "
                "Treat this topic as the dominant angle, going to maximum depth."
            )

    memory_block = build_memory_context() if use_memory else ""
    web_block = build_web_context(clean_input, topic) if use_web else ""
    techniques_block = get_technique_boost(techniques or DEFAULT_TECHNIQUES)

    if mode == "quick":
        return (QUICK_PROMPT
                .replace("{USER_INPUT}", clean_input.strip())
                .replace("{TOPIC_FOCUS}", topic_block)
                .replace("{MEMORY_CONTEXT}", memory_block)
                .replace("{WEB_CONTEXT}", web_block)
                .replace("{TECHNIQUE_BLOCK}", techniques_block)
                .replace("{METACOMMANDS}", meta_block))

    # mode == "full" — original 12-section manifest
    combined_prefix = techniques_block
    if meta_block:
        combined_prefix = techniques_block + "\n" + meta_block

    return (META_PROMPT
            .replace("{USER_INPUT}", clean_input.strip())
            .replace("{TOPIC_FOCUS}", topic_block)
            .replace("{MEMORY_CONTEXT}", memory_block)
            .replace("{WEB_CONTEXT}", web_block)
            .replace("---\n\n## USER INPUT",
                     f"{combined_prefix}\n\n---\n\n## USER INPUT"))


# ----------------------------------------------------------------------
# Metacommand system — /slash modifiers applied at prompt build time
# ----------------------------------------------------------------------

METACOMMANDS: Dict[str, str] = {
    # ── Persona ──────────────────────────────────────────────────────
    "/expert":       "You are a certified senior expert with 20+ years in this domain. Write with authority and precision. Avoid generalities and hedging.",
    "/humain":       "Use a warm, conversational tone. Write as a knowledgeable friend, not a textbook.",
    "/enfant":       "Explain as if to a curious 10-year-old. Short sentences, simple words, concrete analogies only.",
    "/philosophe":   "Approach from a philosophical angle. Question assumptions, explore underlying principles, reference relevant frameworks.",
    "/sceptique":    "Adopt a critical, skeptical stance. Challenge every claim. Identify weaknesses, counterarguments, and what remains uncertain.",
    "/mentor":       "Take the role of a supportive mentor. Acknowledge difficulty, give practical guidance, encourage clear next steps.",
    "/cynique":      "Use dry, sardonic wit. See through optimism. Be realistic without being unhelpful.",
    "/serieux":      "Strictly formal and professional. No humor, no colloquialisms. Dense, structured, precise.",
    "/humour":       "Inject genuine humor throughout: puns, observations, light irony. Make the content memorable.",
    "/emphatique":   "Acknowledge the difficulty or importance of the topic first. Show understanding, then provide substance.",
    "/psychologue":  "Analyze cognitive and behavioral dimensions. Identify patterns and biases — do not invent motivations.",
    "/avocat":       "Build the strongest possible logical defense of the position. State clearly that this is advocacy, not objective truth.",
    "/journaliste":  "Write with journalistic rigor. Use real sources or clearly labeled hypothetical references only. No invented citations.",
    # ── Format ───────────────────────────────────────────────────────
    "/tableau":      "Structure the entire response as one or more tables. Rows and columns must be logically organized.",
    "/json":         "Output only valid JSON. No text before or after. Include an explicit schema in a leading comment.",
    "/markdown":     "Use rich Markdown: headers, bold, italic, code blocks, lists. Optimize for readability.",
    "/code":         "Illustrate with concrete, runnable code examples where applicable. Prefer examples over abstract description.",
    "/points":       "Structure as a numbered or bulleted list. Each item must be self-contained and substantive.",
    "/checklist":    "Output a markdown checklist. Each item is actionable. Group by category if more than 7 items.",
    # ── Depth / Length ───────────────────────────────────────────────
    "/resume":       "Summarize in maximum 5 bullet points. Each captures one essential idea. No filler.",
    "/concis":       "Maximum 50 words. Every word must carry weight. Cut everything else.",
    "/detaille":     "Write between 500 and 1000 words. Develop every point fully. No shortcuts.",
    "/urgent":       "Skip all preamble. Deliver the actionable answer immediately, first line.",
    "/silence":      "Output only the direct answer. No preamble, no explanation, no conclusion.",
    "/minimal":      "Bare minimum: the core answer and one sentence of essential context. Nothing else.",
    # ── Reasoning ────────────────────────────────────────────────────
    "/raisonnement": "Walk through your reasoning step by step before giving the final answer. Show the thinking path, not just the conclusion.",
    "/etapes":       "Break down into clearly numbered sequential steps. Each step: what to do, why, expected output.",
    "/exemple":      "Begin with a concrete real-world example before any theory or abstraction.",
    "/analogie":     "Explain using two analogies from everyday life. Then discuss the limits of each.",
    "/pourcontre":   "Structure as PROS / CONS with equal depth on each side. Conclude with a synthesized recommendation.",
    "/debat":        "Present as a debate between two named experts with opposing views. Summarize consensus at the end.",
    "/reverse":      "Argue the opposite of the expected answer first. Then reconcile by explaining when each position holds.",
    "/iterer":       "Produce 3 distinct versions: V1 (minimal), V2 (standard), V3 (exhaustive).",
    "/ameliorer":    "Identify 3 weaknesses in how this is typically approached. Then rewrite addressing each weakness explicitly.",
    "/reword":       "Restate the question in your own words before answering to confirm understanding.",
    "/critique":     "List every flaw, gap, assumption, and risk in this topic or approach. Be thorough and unsympathetic.",
    "/audit":        "Systematic audit: check for errors, inconsistencies, omissions, and logic or security issues.",
    "/comparatif":   "Compare at least 3 distinct approaches on the same criteria. Use a table for the comparison matrix.",
    # ── Context ──────────────────────────────────────────────────────
    "/historique":   "Ground the answer in historical context. Trace evolution from origin to present state.",
    "/futuriste":    "Project 10 to 50 years forward. What changes? What are the implications and risks?",
    "/questionner":  "Do not answer directly. Ask 3 to 5 clarifying questions that would lead to a better answer.",
    "/neuf":         "Treat this as a completely independent request. Ignore all previous context in this session.",
    "/priorite":     "Focus primarily on the most recent instruction. Other context is secondary.",
    # ── Quality ──────────────────────────────────────────────────────
    "/precision":    "Signal your confidence level for each claim (high / medium / low). Distinguish facts from interpretations.",
    "/hypotheses":   "List all assumptions you are making before answering. For each, state its validity and impact if wrong.",
    "/sources":      "Support each factual claim with a real source or, if unavailable, a clearly labeled hypothetical reference.",
    "/risques":      "Identify and categorize risks: technical, legal, operational, ethical. Rate each by likelihood and impact.",
    "/decision":     "End with a clear, argued recommendation. State what you would do and why.",
    "/verification": "Before outputting, verify internal consistency. Flag any contradiction or uncertainty explicitly.",
    "/confiance":    "For each factual claim, assign a confidence percentage (0–100%) and justify it briefly.",
    "/questions":    "End with the 3 best follow-up questions a curious expert would ask next.",
    "/sansbuzz":     "Avoid all buzzwords, marketing language, and jargon. Use plain, direct language only.",
}


def parse_metacommands(text: str) -> Tuple[str, str]:
    """
    Extract /slash tokens from the task text.
    Returns (cleaned_task, instruction_block).
    The instruction_block is empty string if no metacommands were found.
    """
    tokens = text.split()
    instructions: List[str] = []
    clean: List[str] = []

    for token in tokens:
        if not token.startswith("/"):
            clean.append(token)
            continue

        low = token.lower()

        # Parametric: /limite:N
        if low.startswith("/limite:"):
            try:
                n = int(low.split(":", 1)[1])
                instructions.append(f"Maximum response length: {n} words. Do not exceed this limit.")
            except ValueError:
                clean.append(token)
            continue

        # Parametric: /niveau:X
        if low.startswith("/niveau:"):
            level_raw = low.split(":", 1)[1]
            level_map = {
                "debutant": "beginner", "débutant": "beginner", "beginner": "beginner",
                "intermediaire": "intermediate", "intermédiaire": "intermediate", "intermediate": "intermediate",
                "expert": "expert", "avance": "advanced", "avancé": "advanced",
            }
            level = level_map.get(level_raw, level_raw)
            instructions.append(f"Calibrate depth, vocabulary, and assumed knowledge for a {level}-level audience.")
            continue

        # Parametric: /confiance (with or without value)
        if low.startswith("/confiance"):
            instructions.append("For each factual claim, assign a confidence percentage (0–100%) and justify it briefly.")
            continue

        if low in METACOMMANDS:
            instructions.append(METACOMMANDS[low])
        else:
            # Unknown /command — pass through as literal text
            clean.append(token)

    cleaned = " ".join(clean).strip()

    if not instructions:
        return cleaned, ""

    block = (
        "\n## ACTIVE METACOMMANDS — APPLY STRICTLY\n"
        "The following behavioral directives override default style, format, and depth:\n\n"
        + "\n".join(f"- {instr}" for instr in instructions)
        + "\n"
    )
    return cleaned, block


def split_topics(topics_raw: str) -> List[str]:
    """Parse a user‑supplied topics string into a list of non‑empty topics."""
    if not topics_raw or not topics_raw.strip():
        return []
    # split on newline, comma, or semicolon; allow dashes/bullets as decorations
    parts = re.split(r"[\n;,]+", topics_raw)
    return [p.strip(" -*\t") for p in parts if p.strip(" -*\t")]


# ----------------------------------------------------------------------
# Core generation logic
# ----------------------------------------------------------------------
def generate_multi_topics(
    model: str,
    user_input: str,
    topics_raw: str,
    temperature: float,
    use_memory: bool,
    ollama_url: str,
    timeout: int,
    techniques: Optional[List[int]] = None,
    use_web: bool = True,
    stream_callback=None,
    mode: str = "full",
) -> str:
    if not user_input.strip():
        raise ValueError("Task description must not be empty.")
    topics = split_topics(topics_raw)
    if not topics:
        topics = [""]
    chunks = []
    for idx, topic in enumerate(topics, 1):
        label = topic if topic else "prompt"
        logger.debug(f"Generating {idx}/{len(topics)} for model {model}: '{label}'")
        prompt = build_full_prompt(user_input, topic, use_memory, techniques, use_web, mode)
        if stream_callback:
            text = query_ollama_stream(model, prompt, temperature, num_predict=-1, timeout=timeout, ollama_url=ollama_url, callback=stream_callback)
        else:
            text = query_ollama(model, prompt, temperature, num_predict=-1, timeout=timeout, ollama_url=ollama_url)
        chunks.append(
            f"\n\n{'='*70}\nOUTPUT {idx} / {len(topics)} - TOPIC: {label}\n{'='*70}\n\n{text}"
        )
    full = "".join(chunks)
    append_session({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input,
        "model": model,
        "topics": [t for t in topics if t],
        "mode": "multi_topics",
        "techniques": techniques or DEFAULT_TECHNIQUES,
        "web_enriched": use_web and check_internet(),
    })
    return full


def generate_parallel_both(
    user_input: str,
    topics_raw: str,
    temperature: float,
    use_memory: bool,
    ollama_url: str,
    timeout: int,
    model_a: str = DEFAULT_MODEL_A,
    model_b: str = DEFAULT_MODEL_B,
    techniques: Optional[List[int]] = None,
    use_web: bool = True,
    live_display: bool = False,
) -> Tuple[str, str, Path, Path]:
    if not user_input.strip():
        raise ValueError("Task description must not be empty.")
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

    if live_display and sys.stdout.isatty():
        pane = DualPaneDisplay(model_a, model_b)

        def worker_a():
            return generate_multi_topics(
                model_a, user_input, topics_raw, temperature, use_memory,
                ollama_url, timeout, techniques, use_web, stream_callback=pane.feed_a,
            )

        def worker_b():
            return generate_multi_topics(
                model_b, user_input, topics_raw, temperature, use_memory,
                ollama_url, timeout, techniques, use_web, stream_callback=pane.feed_b,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            fa = pool.submit(worker_a)
            fb = pool.submit(worker_b)
            out_a = fa.result()
            out_b = fb.result()
        print("\n")
    else:
        def worker(model):
            return generate_multi_topics(model, user_input, topics_raw, temperature, use_memory, ollama_url, timeout, techniques, use_web)

        with ThreadPoolExecutor(max_workers=2) as pool:
            fa = pool.submit(worker, model_a)
            fb = pool.submit(worker, model_b)
            out_a = fa.result()
            out_b = fb.result()

    file_a = OUTPUT_DIR / f"{session_id}_{model_a.replace(':','_')}.md"
    file_b = OUTPUT_DIR / f"{session_id}_{model_b.replace(':','_')}.md"

    header_a = f"# Manifest -- {model_a}\n\nTask: {user_input}\nTopics: {topics_raw or '(global)'}\nGenerated: {session_id}\n\n---\n"
    header_b = f"# Manifest -- {model_b}\n\nTask: {user_input}\nTopics: {topics_raw or '(global)'}\nGenerated: {session_id}\n\n---\n"

    file_a.write_text(header_a + out_a, encoding="utf-8")
    file_b.write_text(header_b + out_b, encoding="utf-8")
    logger.info(f"Parallel output written to {file_a} and {file_b}")

    append_session({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input,
        "session_id": session_id,
        "topics": split_topics(topics_raw),
        "mode": "parallel_both",
        "files": [str(file_a.name), str(file_b.name)],
        "techniques": techniques or DEFAULT_TECHNIQUES,
        "web_enriched": use_web and check_internet(),
    })
    return out_a, out_b, file_a, file_b


def run_synthesis(
    user_input: str,
    manifest_a: str,
    manifest_b: str,
    temperature: float,
    use_memory: bool,
    ollama_url: str,
    timeout: int,
    synthesis_model: str = DEFAULT_SYNTH_MODEL,
    techniques: Optional[List[int]] = None,
    stream: bool = False,
    model_a_name: str = "",
    model_b_name: str = "",
) -> Tuple[str, Path]:
    """
    Generate a meta‑synthesis from two manifest texts.
    Returns (synthesis_text, output_path).
    """
    if not manifest_a.strip() or not manifest_b.strip():
        raise ValueError("Both manifests must contain text.")
    if manifest_a.startswith("[ERREUR") or manifest_b.startswith("[ERREUR"):
        raise ValueError("One of the manifests contains an error; cannot synthesise.")

    techniques_block = get_technique_boost(techniques or DEFAULT_TECHNIQUES)

    memory_block = build_memory_context() if use_memory else ""
    prompt = (SYNTH_PROMPT
              .replace("{USER_INPUT}", user_input.strip() or "(not provided)")
              .replace("{MODEL_A}", model_a_name or DEFAULT_MODEL_A)
              .replace("{MODEL_B}", model_b_name or DEFAULT_MODEL_B)
              .replace("{MANIFEST_A}", manifest_a.strip())
              .replace("{MANIFEST_B}", manifest_b.strip())
              .replace("{MEMORY_CONTEXT}", memory_block)
              .replace("# INPUTS", f"{techniques_block}\n\n# INPUTS"))

    ctx_size = max(16384, len(prompt) // 3)

    logger.info("Starting expert synthesis ...")
    if stream and sys.stdout.isatty():
        print(f"\n{'='*62}")
        print(f"  SYNTHESIS IN PROGRESS — {synthesis_model}")
        print(f"{'='*62}\n")
        def stream_print(token):
            sys.stdout.write(token)
            sys.stdout.flush()
        synthesis = query_ollama_stream(
            synthesis_model, prompt, temperature,
            num_predict=-1, timeout=timeout, ollama_url=ollama_url,
            callback=stream_print, num_ctx=ctx_size,
        )
        print("\n")
    else:
        synthesis = query_ollama(synthesis_model, prompt, temperature,
                                 num_predict=-1, timeout=timeout, ollama_url=ollama_url,
                                 num_ctx=ctx_size)

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_synth_" + uuid.uuid4().hex[:6]
    out_file = OUTPUT_DIR / f"{session_id}_synthesis.md"
    header = (f"# Expert Synthesis\n\nTask: {user_input}\n"
              f"Synthesis model: {synthesis_model}\nGenerated: {session_id}\n\n---\n")
    out_file.write_text(header + synthesis, encoding="utf-8")
    logger.info(f"Synthesis saved to {out_file}")

    append_session({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_input": user_input,
        "session_id": session_id,
        "mode": "synthesis",
        "files": [str(out_file.name)],
        "techniques": techniques or DEFAULT_TECHNIQUES,
    })
    return synthesis, out_file


def run_full_pipeline(
    user_input: str,
    topics_raw: str,
    temperature: float,
    use_memory: bool,
    ollama_url: str,
    timeout: int,
    model_a: str,
    model_b: str,
    synthesis_model: str,
    techniques: Optional[List[int]] = None,
    use_web: bool = True,
    live_display: bool = False,
    stream: bool = False,
):
    out_a, out_b, fa, fb = generate_parallel_both(
        user_input, topics_raw, temperature, use_memory, ollama_url, timeout,
        model_a, model_b, techniques, use_web, live_display,
    )
    synthesis, fs = run_synthesis(
        user_input, out_a, out_b, temperature, use_memory, ollama_url, timeout,
        synthesis_model, techniques, stream=stream,
        model_a_name=model_a, model_b_name=model_b,
    )
    return out_a, out_b, fa, fb, synthesis, fs


# ----------------------------------------------------------------------
# CLI definition
# ----------------------------------------------------------------------
def parse_techniques(techniques_raw: str) -> List[int]:
    """Parse comma-separated technique IDs or ranges."""
    if not techniques_raw or not techniques_raw.strip():
        return DEFAULT_TECHNIQUES
    result = []
    for part in techniques_raw.split(","):
        part = part.strip()
        if "-" in part:
            # Range format: 1-5
            try:
                start, end = part.split("-")
                result.extend(range(int(start.strip()), int(end.strip()) + 1))
            except ValueError:
                logger.warning(f"Invalid range format: {part}")
        else:
            try:
                result.append(int(part))
            except ValueError:
                logger.warning(f"Invalid technique ID: {part}")
    return sorted(set(result))


def common_args(parser: argparse.ArgumentParser):
    """Add arguments common to all generation commands."""
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="LLM temperature")
    parser.add_argument("--ollama-url", default=OLLAMA_URL, help="Ollama API endpoint")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout per Ollama call (seconds)")
    parser.add_argument("--no-memory", action="store_true", default=False, help="Disable session memory context")
    parser.add_argument("--techniques", default="", help="Comma-separated technique IDs (e.g. 1,5,8 or 1-10)")
    parser.add_argument("--list-techniques", action="store_true", help="List all available prompt engineering techniques")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate reproducible instruction manifests via Ollama.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate manifest with a single model")
    gen_parser.add_argument("task", help="Task description")
    gen_parser.add_argument("--topic", action="append", dest="topics", help="Topic(s) to focus on (repeatable)")
    gen_parser.add_argument("--model", default=DEFAULT_MODEL_A, help="Ollama model name")
    gen_parser.add_argument("--output", help="Output file (if omitted, auto‑generated)")
    common_args(gen_parser)

    # parallel
    par_parser = subparsers.add_parser("parallel", help="Generate manifests from two models in parallel")
    par_parser.add_argument("task", help="Task description")
    par_parser.add_argument("--topic", action="append", dest="topics", help="Topic(s) (repeatable)")
    par_parser.add_argument("--model-a", default=DEFAULT_MODEL_A, help="First model")
    par_parser.add_argument("--model-b", default=DEFAULT_MODEL_B, help="Second model")
    common_args(par_parser)

    # synthesis
    synth_parser = subparsers.add_parser("synthesis", help="Run expert synthesis on two existing manifests")
    synth_parser.add_argument("task", help="Original task description")
    synth_parser.add_argument("file_a", type=Path, help="Path to manifest A (text file)")
    synth_parser.add_argument("file_b", type=Path, help="Path to manifest B (text file)")
    synth_parser.add_argument("--synthesis-model", default=DEFAULT_SYNTH_MODEL, help="Model for synthesis")
    synth_parser.add_argument("--output", help="Output file")
    common_args(synth_parser)

    # full pipeline
    full_parser = subparsers.add_parser("full", help="Full pipeline: parallel generation + synthesis")
    full_parser.add_argument("task", help="Task description")
    full_parser.add_argument("--topic", action="append", dest="topics", help="Topic(s) (repeatable)")
    full_parser.add_argument("--model-a", default=DEFAULT_MODEL_A)
    full_parser.add_argument("--model-b", default=DEFAULT_MODEL_B)
    full_parser.add_argument("--synthesis-model", default=DEFAULT_SYNTH_MODEL)
    common_args(full_parser)

    # memory
    mem_parser = subparsers.add_parser("memory", help="Manage session memory")
    mem_sub = mem_parser.add_subparsers(dest="mem_cmd", required=True)
    mem_sub.add_parser("view", help="Display memory contents")
    mem_sub.add_parser("clear", help="Erase all memory")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Handle --list-techniques flag if present
    if hasattr(args, "list_techniques") and args.list_techniques:
        print("Available Prompt Engineering Techniques:")
        print("=" * 80)
        if CATEGORIES_DB:
            for cat in CATEGORIES_DB:
                print(f"\n[{cat['id'].upper()}] {cat['name']}")
                print(f"{cat.get('description', '')}")
                print("-" * 60)
                for tech in cat.get("techniques", []):
                    print(f"{tech['id']:3d}. {tech['title']}")
                    print(f"      {tech['description']}\n")
        else:
            for tid in sorted(TECHNIQUES_DB.keys()):
                tech = TECHNIQUES_DB[tid]
                print(f"{tid:3d}. {tech['title']}")
                print(f"      {tech['description']}\n")
        return

    use_memory = not args.no_memory if hasattr(args, "no_memory") else True
    techniques = parse_techniques(args.techniques) if hasattr(args, "techniques") else DEFAULT_TECHNIQUES

    try:
        if args.command == "generate":
            topics_raw = "\n".join(args.topics) if args.topics else ""
            result = generate_multi_topics(
                model=args.model,
                user_input=args.task,
                topics_raw=topics_raw,
                temperature=args.temperature,
                use_memory=use_memory,
                ollama_url=args.ollama_url,
                timeout=args.timeout,
                techniques=techniques,
            )
            if args.output:
                Path(args.output).write_text(result, encoding="utf-8")
                logger.info(f"Output written to {args.output}")
            else:
                print(result)

        elif args.command == "parallel":
            topics_raw = "\n".join(args.topics) if args.topics else ""
            out_a, out_b, fa, fb = generate_parallel_both(
                args.task, topics_raw, args.temperature, use_memory,
                args.ollama_url, args.timeout, args.model_a, args.model_b, techniques,
            )
            print(f"Model {args.model_a} output -> {fa}")
            print(f"Model {args.model_b} output -> {fb}")

        elif args.command == "synthesis":
            manifest_a = args.file_a.read_text(encoding="utf-8")
            manifest_b = args.file_b.read_text(encoding="utf-8")
            synthesis, out_path = run_synthesis(
                args.task, manifest_a, manifest_b, args.temperature, use_memory,
                args.ollama_url, args.timeout, args.synthesis_model, techniques,
            )
            if args.output:
                Path(args.output).write_text(synthesis, encoding="utf-8")
                logger.info(f"Synthesis written to {args.output}")
            else:
                print(f"Synthesis saved to {out_path}")

        elif args.command == "full":
            topics_raw = "\n".join(args.topics) if args.topics else ""
            out_a, out_b, fa, fb, synthesis, fs = run_full_pipeline(
                args.task, topics_raw, args.temperature, use_memory,
                args.ollama_url, args.timeout, args.model_a, args.model_b, args.synthesis_model, techniques,
            )
            print(f"Model {args.model_a} manifest: {fa}")
            print(f"Model {args.model_b} manifest: {fb}")
            print(f"Expert synthesis: {fs}")

        elif args.command == "memory":
            if args.mem_cmd == "view":
                print(view_memory())
            elif args.mem_cmd == "clear":
                clear_memory()
                print("Memory cleared.")

    except (ValueError, RuntimeError, TimeoutError) as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(130)


# ----------------------------------------------------------------------
# Interactive launcher
# ----------------------------------------------------------------------
SETTINGS_FILE = BASE_DIR / "settings.json"


def load_settings() -> dict:
    defaults = {
        "model_a": DEFAULT_MODEL_A,
        "model_b": DEFAULT_MODEL_B,
        "synthesis_model": DEFAULT_SYNTH_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "timeout": DEFAULT_TIMEOUT,
        "ollama_url": OLLAMA_URL,
        "techniques": list(DEFAULT_TECHNIQUES),
        "use_web": True,
        "stream": True,
        "output_mode": "full",
    }
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults.update(saved)
        except (json.JSONDecodeError, Exception):
            pass

    # Type-coerce every field so a corrupt settings.json never breaks the session
    try:
        defaults["temperature"] = float(defaults["temperature"])
        if not 0.0 <= defaults["temperature"] <= 2.0:
            defaults["temperature"] = DEFAULT_TEMPERATURE
    except (TypeError, ValueError):
        defaults["temperature"] = DEFAULT_TEMPERATURE

    try:
        defaults["timeout"] = int(defaults["timeout"])
        if defaults["timeout"] < 10:
            defaults["timeout"] = DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        defaults["timeout"] = DEFAULT_TIMEOUT

    if not isinstance(defaults["model_a"], str) or not defaults["model_a"].strip():
        defaults["model_a"] = DEFAULT_MODEL_A
    if not isinstance(defaults["model_b"], str) or not defaults["model_b"].strip():
        defaults["model_b"] = DEFAULT_MODEL_B
    if not isinstance(defaults["synthesis_model"], str) or not defaults["synthesis_model"].strip():
        defaults["synthesis_model"] = DEFAULT_SYNTH_MODEL

    if not isinstance(defaults["techniques"], list):
        defaults["techniques"] = list(DEFAULT_TECHNIQUES)
    else:
        valid = [int(t) for t in defaults["techniques"] if str(t).lstrip("-").isdigit() and int(t) > 0]
        defaults["techniques"] = valid if valid else list(DEFAULT_TECHNIQUES)

    defaults["use_web"] = bool(defaults.get("use_web", True))
    defaults["stream"] = bool(defaults.get("stream", True))

    if defaults.get("output_mode") not in ("quick", "full"):
        defaults["output_mode"] = "full"

    return defaults


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def prompt_input(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else default


def prompt_int(label: str, default: int) -> int:
    val = input(f"  {label} [{default}]: ").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"    Invalid value, using {default}")
        return default


def prompt_float(label: str, default: float) -> float:
    val = input(f"  {label} [{default}]: ").strip()
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        print(f"    Invalid value, using {default}")
        return default


def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def print_banner(settings: dict):
    inet = "ON" if check_internet() else "OFF"
    web_st = "ON" if settings.get("use_web", True) and check_internet() else "OFF"
    stream_st = "ON" if settings.get("stream", True) else "OFF"
    print("=" * 62)
    print("   PRO-PROMPT  —  Expert Prompt Enhancement Tool  v2.2")
    print("=" * 62)
    print(f"   Model A     : {settings['model_a']}")
    print(f"   Model B     : {settings['model_b']}")
    print(f"   Synthesis   : {settings['synthesis_model']}")
    print(f"   Temperature : {settings['temperature']}")
    mode_label = "QUICK (enhanced prompt)" if settings.get("output_mode") == "quick" else "FULL (12-section manifest)"
    print(f"   Techniques  : {len(settings['techniques'])} active / {len(TECHNIQUES_DB)} available")
    print(f"   Output mode : {mode_label}")
    print(f"   Internet    : {inet}   Web enrichment : {web_st}   Streaming : {stream_st}")
    print("-" * 62)


def print_menu():
    print()
    print("  1.  Single generation         (1 model, streaming)")
    print("  2.  Parallel generation       (2 models, split screen)")
    print("  3.  Full pipeline             (parallel + synthesis)")
    print("  4.  Synthesize 2 files")
    print()
    print("  5.  Configure models")
    print("  6.  Configure techniques")
    print("  7.  Browse available techniques")
    print("  8.  Advanced settings          (temperature, timeout, url, web, stream)")
    print()
    print("  9.  View memory")
    print("  10. Clear memory")
    print()
    print("  h.  Help — metacommands & usage")
    print("  0.  Quit")
    print()


def print_help():
    print()
    print("  " + "=" * 58)
    print("  PRO-PROMPT — Help")
    print("  " + "=" * 58)
    print()
    print("  HOW IT WORKS")
    print("  Enter your prompt in STEP 1. The tool enhances it using")
    print("  173 prompt-engineering techniques and sends the result to")
    print("  a local Ollama model. Output is saved to outputs/")
    print()
    print("  /SLASH METACOMMANDS  (type them in STEP 1 or STEP 2)")
    print("  ─" * 29)
    print("  Persona  : /expert /humain /enfant /philosophe /sceptique")
    print("             /mentor /cynique /serieux /humour /emphatique")
    print("  Format   : /tableau /json /markdown /points /checklist /code")
    print("  Depth    : /resume /concis /detaille /urgent /silence")
    print("             /minimal /limite:N  (e.g. /limite:200)")
    print("  Reasoning: /raisonnement /etapes /exemple /analogie")
    print("             /pourcontre /debat /reverse /iterer /ameliorer")
    print("             /critique /audit /comparatif")
    print("  Quality  : /precision /hypotheses /sources /risques")
    print("             /decision /verification /confiance /questions")
    print("             /sansbuzz")
    print("  Context  : /historique /futuriste /questionner /neuf")
    print("             /priorite /niveau:X  (debutant|intermediaire|expert)")
    print()
    print("  EXAMPLES")
    print("  > /expert /raisonnement Build a REST API in Python")
    print("  > /enfant /analogie Explain quantum computing")
    print("  > /json /critique Analyze this architecture: [description]")
    print()
    print("  TIPS FOR NOOBS")
    print("  - STEP 2 and STEP 3 are optional — just press ENTER to skip")
    print("  - STEP 4 shows your local models — pick by number")
    print("  - Option 6 lets you change which techniques are applied")
    print("  - Outputs are saved in outputs/ as .md files")
    print()
    print("  " + "=" * 58)
    print()
    input("  Press ENTER to return to menu...")


_METHOD_GROUPS = [
    ("Persona ",  "/expert /humain /enfant /philosophe /sceptique /mentor /cynique /serieux /humour /emphatique"),
    ("Format  ",  "/tableau /json /markdown /points /checklist /code"),
    ("Depth   ",  "/resume /concis /detaille /urgent /silence /minimal /limite:N"),
    ("Reason  ",  "/raisonnement /etapes /exemple /analogie /pourcontre /debat /reverse /iterer /ameliorer /critique /audit /comparatif"),
    ("Quality ",  "/precision /hypotheses /sources /risques /decision /verification /confiance /questions /sansbuzz"),
    ("Context ",  "/historique /futuriste /questionner /neuf /priorite /niveau:X"),
]

_MODEL_NAME_RE = re.compile(r"^[a-zA-Z0-9._:/\-]+$")
_MAX_TASK_LEN  = 8000
_MAX_TOPIC_LEN = 500
_MAX_MODEL_LEN = 100


def sanitize_input(value: str, kind: str = "text") -> str:
    """Zero-trust sanitizer for all user-provided strings.

    kind='text'  — task / topic text (strip null bytes, control chars, cap length)
    kind='model' — model name (allow only safe identifier chars, cap at 100)
    kind='url'   — ollama URL (must be http/https, host localhost/127.0.0.1 only)
    """
    if not isinstance(value, str):
        return ""
    # Strip null bytes and ASCII control characters (keep \n \t for text)
    value = value.replace("\x00", "")
    if kind != "text":
        value = re.sub(r"[\x00-\x1f\x7f]", "", value)

    if kind == "model":
        value = value.strip()[:_MAX_MODEL_LEN]
        if not _MODEL_NAME_RE.match(value):
            # Remove any character that doesn't match the allowed set
            value = re.sub(r"[^a-zA-Z0-9._:/\-]", "", value)
        return value

    if kind == "url":
        value = value.strip()
        try:
            from urllib.parse import urlparse as _urlparse
            p = _urlparse(value)
            if p.scheme not in ("http", "https"):
                return ""
            if p.hostname not in ("localhost", "127.0.0.1", "::1"):
                return ""
        except Exception:
            return ""
        return value

    # kind == "text" (default) — always allow up to task max; callers slice further if needed
    value = value[:_MAX_TASK_LEN]
    return value.strip()


def collect_input(settings: dict) -> Tuple[str, str, str]:
    """
    Four-step input: prompt → methods → topic → model.
    Returns (full_task_with_metacommands, topics_raw, model_name).
    Runs without any further prompts after this.
    """
    print()
    print("  ─" * 31)
    print("  STEP 1 — Prompt to enhance")
    print("  ─" * 31)
    raw_task = input("  > ").strip()
    task = sanitize_input(raw_task, "text")
    if not task:
        print("  [!] Prompt cannot be empty.")
        return "", "", ""

    print()
    print("  ─" * 31)
    print("  STEP 2 — Methods  (ENTER to skip)")
    for label, cmds in _METHOD_GROUPS:
        print(f"  {label}: {cmds}")
    print("  ─" * 31)
    methods_raw = sanitize_input(input("  > ").strip(), "text")

    # Merge any /commands already in the task with those typed in step 2
    task_cmds = [t for t in task.split() if t.startswith("/")]
    task_clean = " ".join(t for t in task.split() if not t.startswith("/"))
    extra_cmds = [t for t in methods_raw.split() if t.startswith("/")]
    all_cmds = task_cmds + extra_cmds

    if all_cmds:
        print(f"  [active] {' '.join(all_cmds)}")
        full_task = " ".join(all_cmds) + " " + task_clean
    else:
        full_task = task_clean

    print()
    print("  ─" * 31)
    print("  STEP 3 — Topic focus  (ENTER to skip)")
    print("  ─" * 31)
    topics_raw = sanitize_input(input("  > ").strip(), "text")[:_MAX_TOPIC_LEN]

    print()
    print("  ─" * 31)
    print("  STEP 4 — Model")
    print("  ─" * 31)
    chosen_model = pick_model_interactive("Select model", settings.get("model_a", DEFAULT_MODEL_A))

    return full_task.strip(), topics_raw, chosen_model


def menu_generate(settings: dict):
    task, topics_raw, model = collect_input(settings)
    if not task:
        return
    use_web = settings.get("use_web", True)
    do_stream = settings.get("stream", True) and sys.stdout.isatty()
    mode = settings.get("output_mode", "full")

    print(f"\n  → Model: {model}  |  Mode: {mode.upper()}")
    if use_web and check_internet():
        print("  → Web enrichment: ON")
    if do_stream:
        print(f"\n  {'─' * 58}\n")

    def print_token(t):
        sys.stdout.write(t)
        sys.stdout.flush()

    try:
        result = generate_multi_topics(
            model=model,
            user_input=task,
            topics_raw=topics_raw,
            temperature=settings["temperature"],
            use_memory=True,
            ollama_url=settings["ollama_url"],
            timeout=settings["timeout"],
            techniques=settings["techniques"],
            use_web=use_web,
            stream_callback=print_token if do_stream else None,
            mode=mode,
        )
        if do_stream:
            print("\n")
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        out_file = OUTPUT_DIR / f"{session_id}_{model.replace(':', '_')}.md"
        out_file.write_text(result, encoding="utf-8")
        print(f"\n  Saved: outputs/{out_file.name}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERROR] {e}")


def menu_parallel(settings: dict):
    task, topics_raw, model_a = collect_input(settings)
    if not task:
        return
    model_b = pick_model_interactive("Select model B", settings.get("model_b", DEFAULT_MODEL_B))
    use_web = settings.get("use_web", True)
    do_stream = settings.get("stream", True) and sys.stdout.isatty()

    print(f"\n  → Running: {model_a}  vs  {model_b}")
    if use_web and check_internet():
        print("  → Web enrichment: ON")
    if do_stream:
        print("  → Split screen active. Ctrl+C to interrupt.\n")
        time.sleep(1)

    try:
        _, _, fa, fb = generate_parallel_both(
            user_input=task,
            topics_raw=topics_raw,
            temperature=settings["temperature"],
            use_memory=True,
            ollama_url=settings["ollama_url"],
            timeout=settings["timeout"],
            model_a=model_a,
            model_b=model_b,
            techniques=settings["techniques"],
            use_web=use_web,
            live_display=do_stream,
        )
        print(f"\n  Manifest A: {fa}")
        print(f"  Manifest B: {fb}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERROR] {e}")


def menu_full(settings: dict):
    task, topics_raw, model_a = collect_input(settings)
    if not task:
        return
    model_b = pick_model_interactive("Select model B", settings.get("model_b", DEFAULT_MODEL_B))
    synth = pick_model_interactive("Select synthesis model", settings.get("synthesis_model", DEFAULT_SYNTH_MODEL))
    use_web = settings.get("use_web", True)
    do_stream = settings.get("stream", True) and sys.stdout.isatty()

    print(f"\n  → Pipeline: {model_a} + {model_b} → synthesis {synth}")
    if use_web and check_internet():
        print("  → Web enrichment: ON")
    if do_stream:
        print("  → Phase 1: parallel split screen. Phase 2: synthesis streaming.\n")
        time.sleep(1)

    try:
        _, _, fa, fb, _, fs = run_full_pipeline(
            user_input=task,
            topics_raw=topics_raw,
            temperature=settings["temperature"],
            use_memory=True,
            ollama_url=settings["ollama_url"],
            timeout=settings["timeout"],
            model_a=model_a,
            model_b=model_b,
            synthesis_model=synth,
            techniques=settings["techniques"],
            use_web=use_web,
            live_display=do_stream,
            stream=do_stream,
        )
        print(f"\n  Manifest A : {fa}")
        print(f"  Manifest B : {fb}")
        print(f"  Synthesis  : {fs}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERROR] {e}")


def menu_synthesis(settings: dict):
    print()
    existing = sorted(OUTPUT_DIR.glob("*.md"))
    if not existing:
        print("  No files in outputs/. Run a generation first.")
        return
    print("  Available files in outputs/:")
    for i, f in enumerate(existing, 1):
        print(f"    {i:3d}. {f.name}")
    print()
    try:
        idx_a = int(input("  File A number: ").strip()) - 1
        idx_b = int(input("  File B number: ").strip()) - 1
        file_a = existing[idx_a]
        file_b = existing[idx_b]
    except (ValueError, IndexError):
        print("  [!] Invalid selection.")
        return
    task = sanitize_input(input("  Original task (short description):\n  > ").strip(), "text")
    if not task:
        task = "(not provided)"
    synth_model = pick_model_interactive("Synthesis model", settings["synthesis_model"])
    do_stream = settings.get("stream", True) and sys.stdout.isatty()
    print(f"\n  Synthesizing {file_a.name} + {file_b.name} with {synth_model} ...")
    try:
        manifest_a = file_a.read_text(encoding="utf-8")
        manifest_b = file_b.read_text(encoding="utf-8")
        _, out_path = run_synthesis(
            user_input=task,
            manifest_a=manifest_a,
            manifest_b=manifest_b,
            temperature=settings["temperature"],
            use_memory=True,
            ollama_url=settings["ollama_url"],
            timeout=settings["timeout"],
            synthesis_model=synth_model,
            techniques=settings["techniques"],
            stream=do_stream,
        )
        print(f"\n  Synthesis saved: outputs/{Path(out_path).name}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERROR] {e}")


def menu_configure_models(settings: dict):
    print()
    print("  -- Default model configuration --")
    print(f"  Current: A={settings['model_a']}  B={settings['model_b']}  Synth={settings['synthesis_model']}")
    settings["model_a"] = pick_model_interactive("Model A (generation / single)", settings["model_a"])
    settings["model_b"] = pick_model_interactive("Model B (parallel)", settings["model_b"])
    settings["synthesis_model"] = pick_model_interactive("Synthesis model", settings["synthesis_model"])
    save_settings(settings)
    print("\n  Models saved.")


def menu_configure_techniques(settings: dict):
    print()
    print("  -- Technique configuration --")
    current = ",".join(str(t) for t in settings["techniques"])
    print(f"  Active: {current}")
    print()
    total = len(TECHNIQUES_DB)
    print("  Input examples:")
    print("    1,5,8,10,25     ->  specific techniques")
    print("    1-20             ->  range")
    print("    1-10,25,40-50    ->  combination")
    print(f"    all              ->  all ({total} techniques)")
    print("    default          ->  default set")
    print()
    raw = input("  Techniques: ").strip()
    if not raw:
        return
    if raw.lower() == "all":
        settings["techniques"] = sorted(TECHNIQUES_DB.keys())
    elif raw.lower() == "default":
        settings["techniques"] = list(DEFAULT_TECHNIQUES)
    else:
        settings["techniques"] = parse_techniques(raw)
    save_settings(settings)
    print(f"\n  {len(settings['techniques'])} techniques active.")


def _paged_print(lines: List[str], page_size: int = 22):
    """Print lines with ENTER-to-continue paging."""
    for i, line in enumerate(lines):
        print(line)
        if (i + 1) % page_size == 0 and i < len(lines) - 1:
            try:
                cont = input("  -- more -- (ENTER to continue, q to stop) ").strip().lower()
                if cont == "q":
                    return
            except (KeyboardInterrupt, EOFError):
                return


def menu_list_techniques():
    lines = []
    lines.append("")
    lines.append("  Available Prompt Engineering Techniques:")
    lines.append("  " + "=" * 62)
    if CATEGORIES_DB:
        for cat in CATEGORIES_DB:
            lines.append(f"\n  [{cat['id'].upper()}] {cat['name']}")
            lines.append(f"  {cat.get('description', '')}")
            lines.append("  " + "-" * 58)
            for tech in cat.get("techniques", []):
                lines.append(f"  {tech['id']:3d}. {tech['title']}")
                lines.append(f"       {tech['description']}")
    else:
        for tid in sorted(TECHNIQUES_DB.keys()):
            tech = TECHNIQUES_DB[tid]
            lines.append(f"  {tid:3d}. {tech['title']}")
            lines.append(f"       {tech['description']}")
    if ANTI_PATTERNS:
        lines.append(f"\n  [ANTI-PATTERNS] Common mistakes to avoid")
        lines.append("  " + "-" * 58)
        for ap in ANTI_PATTERNS:
            lines.append(f"  ! {ap['name']}: {ap['symptom']}")
            lines.append(f"    Fix: {ap['fix']}")
    if QUICK_REFERENCE:
        lines.append(f"\n  [QUICK REFERENCE] Recommended techniques by task type")
        lines.append("  " + "-" * 58)
        for task_type, ids in QUICK_REFERENCE.items():
            id_str = ",".join(str(i) for i in ids)
            lines.append(f"  {task_type}: {id_str}")
    _paged_print(lines)
    print()
    input("  Press ENTER to return to menu...")


def prompt_bool(label: str, default: bool) -> bool:
    dstr = "yes" if default else "no"
    val = input(f"  {label} [{dstr}] (yes/no): ").strip().lower()
    if not val:
        return default
    return val in ("yes", "y", "oui", "o", "1", "true")


def menu_advanced(settings: dict):
    print()
    print("  -- Advanced settings --")
    settings["temperature"] = prompt_float("Temperature (0.0 - 1.0)", settings["temperature"])
    settings["timeout"] = prompt_int("Timeout per call (seconds)", settings["timeout"])
    raw_url = prompt_input("Ollama URL", settings["ollama_url"])
    settings["ollama_url"] = sanitize_input(raw_url, "url") or settings["ollama_url"]
    settings["use_web"] = prompt_bool("Automatic web enrichment", settings.get("use_web", True))
    settings["stream"] = prompt_bool("Real-time streaming in terminal", settings.get("stream", True))
    print()
    print("  Output mode:")
    print("    quick  —  Single enhanced prompt, ready to paste into any LLM")
    print("    full   —  Exhaustive 12-section instruction manifest (expert)")
    raw_mode = input(f"  Mode [quick/full] [{settings.get('output_mode','full')}]: ").strip().lower()
    if raw_mode in ("quick", "full"):
        settings["output_mode"] = raw_mode
    save_settings(settings)
    print("\n  Settings saved.")


def interactive():
    # Suppress INFO-level log noise in the interactive terminal UI
    logging.disable(logging.INFO)

    settings = load_settings()
    ensure_ollama_ready()
    ensure_models_available(settings)

    _NO_PAUSE = {"0", "q", "quit", "exit", "7", "h", "help", "?"}

    while True:
        clear_screen()
        print_banner(settings)
        print_menu()

        try:
            choice = input("  Choice > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye.\n")
            break

        try:
            if choice == "1":
                menu_generate(settings)
            elif choice == "2":
                menu_parallel(settings)
            elif choice == "3":
                menu_full(settings)
            elif choice == "4":
                menu_synthesis(settings)
            elif choice == "5":
                menu_configure_models(settings)
            elif choice == "6":
                menu_configure_techniques(settings)
            elif choice == "7":
                menu_list_techniques()
            elif choice == "8":
                menu_advanced(settings)
            elif choice == "9":
                print()
                print(view_memory())
            elif choice == "10":
                clear_memory()
                print("\n  Memory cleared.")
            elif choice in ("h", "help", "?"):
                print_help()
            elif choice in ("0", "q", "quit", "exit"):
                print("\n  Goodbye.\n")
                break
            else:
                print("\n  [!] Unknown option. Type h for help.")
        except KeyboardInterrupt:
            print("\n\n  [Interrupted] Returning to menu...")

        if choice not in _NO_PAUSE:
            print()
            input("  Press ENTER to return to menu...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        interactive()
