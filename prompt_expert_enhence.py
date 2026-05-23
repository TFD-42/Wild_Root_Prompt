#!/usr/bin/env python3
"""
Manifest Generator – CLI Tool for Reproducible Instruction Manifests via Ollama.

Usage:
    manifest generate <task> [--topic TOPIC ...] [--model MODEL] [options]
    manifest parallel <task> [--topic TOPIC ...] [options]
    manifest synthesis <task> <file_a> <file_b> [options]
    manifest full <task> [--topic TOPIC ...] [options]
    manifest memory view
    manifest memory clear

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
METHODOLOGY_FILE = BASE_DIR / "prompte_expert_methodologie.json"
DEFAULT_MODEL_A = "llama3:latest"
DEFAULT_MODEL_B = "qwen2.5:7b"
DEFAULT_SYNTH_MODEL = "qwen2.5:7b"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT = 600  # seconds for a single Ollama call
SYNTH_TIMEOUT = 1200   # longer timeout for synthesis

# Technique appliquées par défaut (peuvent être réglées via CLI)
DEFAULT_TECHNIQUES = [1, 5, 8, 10, 12, 14, 18, 25, 40, 47]  # Ensemble minimal de techniques utiles

# Create directories at import time
MEMORY_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Load methodologies from JSON
TECHNIQUES_DB: Dict[int, Dict[str, str]] = {}
def load_methodologies():
    global TECHNIQUES_DB
    if METHODOLOGY_FILE.exists():
        try:
            text = METHODOLOGY_FILE.read_text(encoding="utf-8")
            # Parse JSON-like structure: line = "1. **title** – description"
            lines = text.strip().split("\n")
            for line in lines:
                if line and line[0].isdigit():
                    match = re.match(r"(\d+)\.\s+\*\*(.+?)\*\*\s+–\s+(.+)", line)
                    if match:
                        num = int(match.group(1))
                        title = match.group(2)
                        desc = match.group(3)
                        TECHNIQUES_DB[num] = {"title": title, "description": desc}
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
    print("  [!] Ollama n'est pas installe sur cette machine.")
    print(f"  OS detecte : {os_type}")
    print()
    if os_type == "mac":
        print("  Options d'installation :")
        print("    1. Curl automatique (recommande)")
        print("    2. Annuler")
        c = input("  Choix > ").strip()
        if c != "1":
            return False
        print("\n  Installation en cours ...")
        try:
            subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                check=True,
            )
            print("  Ollama installe avec succes.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  [ERREUR] Installation echouee : {e}")
            return False
    elif os_type == "linux":
        print("  Options d'installation :")
        print("    1. Curl automatique (recommande)")
        print("    2. Annuler")
        c = input("  Choix > ").strip()
        if c != "1":
            return False
        print("\n  Installation en cours ...")
        try:
            subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                check=True,
            )
            print("  Ollama installe avec succes.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  [ERREUR] Installation echouee : {e}")
            return False
    elif os_type == "windows":
        print("  Installation automatique Windows :")
        print("    1. Telecharger et lancer l'installeur (winget)")
        print("    2. Annuler")
        c = input("  Choix > ").strip()
        if c != "1":
            return False
        print("\n  Installation via winget ...")
        try:
            subprocess.run(
                ["winget", "install", "Ollama.Ollama", "--accept-source-agreements", "--accept-package-agreements"],
                check=True,
            )
            print("  Ollama installe avec succes.")
            print("  [!] Redemarrage du terminal peut etre necessaire.")
            return True
        except FileNotFoundError:
            print("  [!] winget non disponible. Tentative avec curl PowerShell ...")
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '$env:TEMP\\OllamaSetup.exe'; Start-Process '$env:TEMP\\OllamaSetup.exe' -Wait"],
                    check=True,
                )
                print("  Installeur lance. Attends la fin de l'installation.")
                return True
            except Exception as e2:
                print(f"  [ERREUR] {e2}")
                print("  Installe manuellement : https://ollama.com/download")
                return False
        except subprocess.CalledProcessError as e:
            print(f"  [ERREUR] {e}")
            return False
    return False


def start_ollama_serve():
    if is_ollama_running():
        return
    print("  Demarrage d'Ollama en arriere-plan ...")
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
                print("  Ollama est pret.")
                return
        print("  [!] Ollama demarre mais pas encore pret. Poursuite quand meme.")
    except Exception as e:
        print(f"  [!] Impossible de demarrer Ollama : {e}")


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
    print(f"\n  Telechargement du modele '{model_name}' ...")
    print("  (Cela peut prendre plusieurs minutes selon la taille)")
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
            print(f"  Modele '{model_name}' telecharge avec succes.")
            return True
        else:
            print(f"  [ERREUR] ollama pull a retourne le code {proc.returncode}")
            return False
    except FileNotFoundError:
        print("  [ERREUR] La commande 'ollama' n'est pas trouvee.")
        return False
    except Exception as e:
        print(f"  [ERREUR] {e}")
        return False


def pick_model_interactive(label: str, current: str) -> str:
    models = list_local_models()
    print()
    if models:
        print(f"  -- {label} --")
        print(f"  Modeles installes localement :")
        for i, m in enumerate(models, 1):
            marker = " <-- actuel" if m["name"] == current else ""
            print(f"    {i:3d}. {m['name']:<30s}  {m['size']:>6s}  {m['modified']}{marker}")
        print(f"    {len(models)+1:3d}. [Entrer un nom manuellement / pull un nouveau modele]")
        print()
        raw = input(f"  Choix [{current}] > ").strip()
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
        print("  Aucun modele installe localement.")
        print()
        raw = ""

    if not raw:
        name = input(f"  Nom du modele a utiliser (ex: llama3:latest, qwen2.5:7b) [{current}] > ").strip()
        if not name:
            return current
        raw = name

    local_names = [m["name"] for m in models]
    if raw not in local_names:
        print(f"\n  Le modele '{raw}' n'est pas installe localement.")
        do_pull = input("  Telecharger maintenant ? (oui/non) [oui] > ").strip().lower()
        if do_pull in ("", "oui", "o", "yes", "y", "1"):
            if pull_model_interactive(raw):
                return raw
            else:
                print(f"  Utilisation du modele precedent : {current}")
                return current
        else:
            print(f"  [!] Le modele '{raw}' sera utilise tel quel (erreur possible si absent).")
    return raw


def ensure_ollama_ready():
    if not is_ollama_installed():
        if not install_ollama_interactive():
            print("\n  [!] Ollama n'est pas disponible. Les generations vont echouer.")
            print("  Installe manuellement : https://ollama.com/download")
            return
    if not is_ollama_running():
        start_ollama_serve()


# ----------------------------------------------------------------------
# Meta‑prompts (unchanged from original, kept for brevity)
# ----------------------------------------------------------------------
META_PROMPT = """
# META-PROMPT : GENERATEUR DE MANIFESTE D'INSTRUCTION REPRODUCTIBLE

> Usage : Copie ce meta-prompt dans n'importe quel agent LLM, puis fournis-lui ta tache dans la section INPUT_UTILISATEUR. Il produira un manifeste-instruction complet, niveau expert prompt engineer, qu'un autre agent LLM pourra executer sans contexte prealable.

---

## ROLE

Tu es un architecte de prompts senior specialise dans la production de manifestes d'instruction reproductibles. Ta mission n'est jamais d'ecrire du code ni d'executer la tache. Ta mission est de produire un document-manifeste qui decrit la tache avec une telle precision methodologique qu'un autre agent LLM (Claude, GPT, Gemini, Llama, Mistral, Qwen) puisse la reproduire integralement avec ses propres methodes d'implementation.

Tu ecris comme un redacteur de RFC, de spec produit, ou d'article technique - pas comme un developpeur. Tu decris le QUOI, le POURQUOI, le DANS QUEL ORDRE, et le COMMENT-CONCEPTUEL - jamais le COMMENT-SYNTAXIQUE.

---

## ENTREE UTILISATEUR

<<<INPUT_UTILISATEUR
{USER_INPUT}
INPUT_UTILISATEUR>>>

{TOPIC_FOCUS}

{MEMORY_CONTEXT}

{WEB_CONTEXT}

---

## REGLES ABSOLUES DE SORTIE

1. Zero ligne de code. Aucun bloc de code. Aucune commande shell brute. Aucune syntaxe d'API.
2. Reproductibilite totale. Un agent LLM different doit pouvoir reproduire le resultat.
3. Agnostique d'implementation.
4. Style manifeste / article / spec. Sections numerotees, titres clairs.
5. Niveau expert. Anticipe les edge cases, les pieges, les ambiguites.
6. Auto-diagnostic d'ambiguite si l'entree est ambigue.
7. Aucune limite de longueur : ecris autant que necessaire pour epuiser le sujet.

---

## STRUCTURE OBLIGATOIRE DU MANIFESTE GENERE

Tu produis exactement les 12 sections suivantes, dans cet ordre :

### § 1. TITRE & RESUME EXECUTIF
### § 2. OBJECTIF FINAL & DEFINITION DE SUCCES
### § 3. CONTEXTE D'EXECUTION & PREREQUIS
### § 4. ZONES D'AMBIGUITE A LEVER
### § 5. DECOMPOSITION EN ETAPES (PIPELINE DETAILLE)
### § 6. BOUCLES DE CONTROLE & SCORING
### § 7. ARTEFACTS PERSISTANTS A MAINTENIR
### § 8. CONTRAINTES & GARDE-FOUS
### § 9. STRATEGIE DE GESTION D'ERREUR
### § 10. LIVRABLE FINAL & FORMAT DE RESTITUTION
### § 11. CHECKLIST DE REPRODUCTIBILITE
### § 12. NOTES POUR L'AGENT DESTINATAIRE

---

## INTERDICTIONS STRICTES

- Aucun bloc de code, quelle que soit la justification.
- Aucune commande shell, requete SQL, appel d'API en syntaxe brute.
- Aucun TODO ou "a completer".
- Aucune mention de toi-meme en tant que generateur.
- Aucun emoji decoratif. Signes acceptes : carre vide pour checklist, fleche pour transitions, § pour sections.

---

Ne produis que le manifeste final. Aucun preambule. Aucune conclusion. Le manifeste commence directement par "## § 1. TITRE & RESUME EXECUTIF".
"""

SYNTH_PROMPT = """
# ROLE
Tu es un META-ARCHITECTE de prompts, expert senior en ingenierie d'instructions LLM/AI/AGI, charge de produire une SYNTHESE FINALE sans aucune limite de longueur.

# MISSION
Tu disposes de deux manifestes d'instruction generes par deux modeles distincts (MODELE A et MODELE B) sur la meme tache utilisateur. Tu dois :

1. ANALYSE COMPARATIVE : passer en revue les deux manifestes, identifier les points de convergence, les divergences, les omissions, les forces et faiblesses respectives.
2. PLAN DIRECTEUR : produire un plan global structure, exhaustif, hierarchise.
3. SYNTHESE UNIFIEE : fusionner et enrichir les deux manifestes en un document maitre superieur a chacun des deux, en gardant le meilleur de chaque, en comblant les manques, en ajoutant les angles morts qu'aucun des deux n'a vus.
4. PROMPT-INSTRUCTION FINAL : a la fin, produire un prompt-instruction expert, de qualite professionnelle, pret a etre injecte tel quel dans un autre agent LLM (Claude, GPT, Gemini, etc.) pour executer la tache au plus haut niveau.

# REGLES
- Aucune limite de longueur : ecris autant que necessaire, sois exhaustif.
- Aucun emoji unicode decoratif.
- Aucun bloc de code executable.
- Style : technique, dense, professionnel, niveau expert AGI prompt engineer.
- Structure obligatoire (sections numerotees ci-dessous).

# STRUCTURE OBLIGATOIRE DE TA SORTIE

## PARTIE I - ANALYSE COMPARATIVE
### I.1 Convergences entre les deux manifestes
### I.2 Divergences notables
### I.3 Omissions et angles morts detectes
### I.4 Score qualitatif par section (tableau)

## PARTIE II - PLAN DIRECTEUR UNIFIE
### II.1 Vision et objectifs strategiques
### II.2 Phases majeures
### II.3 Dependances et ordonnancement
### II.4 Risques critiques et mitigation

## PARTIE III - MANIFESTE SYNTHETIQUE ENRICHI
Reprend les 12 sections classiques (§ 1 a § 12) en version unifiee, enrichie et superieure aux deux entrees.

## PARTIE IV - PROMPT-INSTRUCTION EXPERT FINAL
Un prompt clef en main, autoporteur, sans contexte externe requis, pret a etre colle dans n'importe quel agent LLM pour resoudre la tache. Niveau prompt engineer senior. Inclure : role, contexte, contraintes, methodologie, critere de succes, boucles d'auto-verification, format de livrable.

## PARTIE V - NOTES META
Conseils strategiques pour l'agent destinataire, pieges connus, optimisations possibles.

# ENTREES

## TACHE UTILISATEUR D'ORIGINE
<<<TACHE
{USER_INPUT}
TACHE>>>

## MANIFESTE DU MODELE A ({MODEL_A})
<<<MANIFESTE_A
{MANIFEST_A}
MANIFESTE_A>>>

## MANIFESTE DU MODELE B ({MODEL_B})
<<<MANIFESTE_B
{MANIFEST_B}
MANIFESTE_B>>>

{MEMORY_CONTEXT}

# DEMARRE LA SYNTHESE MAINTENANT
Commence directement par "## PARTIE I - ANALYSE COMPARATIVE". Aucun preambule.
"""

# ----------------------------------------------------------------------
# Persistent memory helpers (thread‑safe with simple lock)
# ----------------------------------------------------------------------
import threading

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
    lines = ["## CONTEXTE MEMOIRE (sessions anterieures, pour coherence)"]
    for s in sessions:
        lines.append(f"- [{s.get('timestamp','?')}] Tache : {s.get('user_input','')[:200]}")
        if s.get("topics"):
            lines.append(f"  Topics traites : {', '.join(s['topics'])}")
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
            headers={"User-Agent": "Mozilla/5.0 (compatible; ManifestGen/2.0)"},
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
            headers={"User-Agent": "Mozilla/5.0 (compatible; ManifestGen/2.0)"},
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
    lines = ["## CONTEXTE WEB (recherche automatique, pour enrichissement)"]
    pages_fetched = 0
    for r in results:
        lines.append(f"- [{r['title']}]({r.get('url', '')})")
        if r.get("snippet"):
            lines.append(f"  Resume: {r['snippet']}")
        if pages_fetched < max_pages and r.get("url"):
            page_text = fetch_page_text(r["url"])
            if page_text:
                lines.append(f"  Extrait: {page_text[:800]}")
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
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": 8192,
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
):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": 8192,
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
            status = f"  A: {len(self.lines_a)} lignes | B: {len(self.lines_b)} lignes"
            output.append(status)

            sys.stdout.write("\n".join(output))
            sys.stdout.flush()

    def get_texts(self) -> Tuple[str, str]:
        return "".join(self.buf_a), "".join(self.buf_b)


def get_technique_boost(technique_ids: List[int]) -> str:
    """Generate prompt enhancement block from selected techniques."""
    if not technique_ids:
        return ""
    blocks = []
    for tid in sorted(technique_ids):
        if tid in TECHNIQUES_DB:
            tech = TECHNIQUES_DB[tid]
            blocks.append(f"- {tech['title']}: {tech['description']}")
    if not blocks:
        return ""
    return (
        "## TECHNIQUES DE PROMPT ENGINEERING A APPLIQUER\n"
        "Integre les methodes suivantes dans ta generation pour une qualite superieure:\n"
        + "\n".join(blocks)
    )


def build_full_prompt(
    user_input: str,
    topic: str = "",
    use_memory: bool = True,
    techniques: Optional[List[int]] = None,
    use_web: bool = True,
) -> str:
    topic_block = ""
    if topic.strip():
        topic_block = (
            "## FOCUS TOPIC\n"
            f"Concentre integralement ce manifeste sur le topic suivant : '{topic.strip()}'. "
            "Traite ce topic comme l'angle dominant, en allant au maximum de profondeur."
        )
    memory_block = build_memory_context() if use_memory else ""
    web_block = build_web_context(user_input, topic) if use_web else ""
    techniques_block = get_technique_boost(techniques or DEFAULT_TECHNIQUES)
    return (META_PROMPT
            .replace("{USER_INPUT}", user_input.strip())
            .replace("{TOPIC_FOCUS}", topic_block)
            .replace("{MEMORY_CONTEXT}", memory_block)
            .replace("{WEB_CONTEXT}", web_block)
            .replace("---\n\n## ENTREE UTILISATEUR",
                     f"{techniques_block}\n\n---\n\n## ENTREE UTILISATEUR"))


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
) -> str:
    if not user_input.strip():
        raise ValueError("Task description must not be empty.")
    topics = split_topics(topics_raw)
    if not topics:
        topics = [""]
    chunks = []
    for idx, topic in enumerate(topics, 1):
        label = topic if topic else "global manifest"
        logger.info(f"Generating {idx}/{len(topics)} for model {model}: '{label}'")
        prompt = build_full_prompt(user_input, topic, use_memory, techniques, use_web)
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
              .replace("{MODEL_A}", DEFAULT_MODEL_A)   # using the defaults for prompt clarity
              .replace("{MODEL_B}", DEFAULT_MODEL_B)
              .replace("{MANIFEST_A}", manifest_a.strip())
              .replace("{MANIFEST_B}", manifest_b.strip())
              .replace("{MEMORY_CONTEXT}", memory_block)
              .replace("# ENTREES", f"{techniques_block}\n\n# ENTREES"))

    logger.info("Starting expert synthesis ...")
    synthesis = query_ollama(synthesis_model, prompt, temperature, num_predict=-1, timeout=timeout, ollama_url=ollama_url)

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
):
    out_a, out_b, fa, fb = generate_parallel_both(
        user_input, topics_raw, temperature, use_memory, ollama_url, timeout,
        model_a, model_b, techniques, use_web, live_display,
    )
    synthesis, fs = run_synthesis(user_input, out_a, out_b, temperature, use_memory, ollama_url, timeout, synthesis_model, techniques)
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
        "techniques": DEFAULT_TECHNIQUES,
        "use_web": True,
        "stream": True,
    }
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults.update(saved)
        except (json.JSONDecodeError, Exception):
            pass
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
        print(f"    Valeur invalide, utilisation de {default}")
        return default


def prompt_float(label: str, default: float) -> float:
    val = input(f"  {label} [{default}]: ").strip()
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        print(f"    Valeur invalide, utilisation de {default}")
        return default


def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def print_banner(settings: dict):
    inet = "ON" if check_internet() else "OFF"
    web_st = "ON" if settings.get("use_web", True) and check_internet() else "OFF"
    stream_st = "ON" if settings.get("stream", True) else "OFF"
    print("=" * 62)
    print("   MANIFEST GENERATOR  -  Prompt Expert Launcher")
    print("=" * 62)
    print(f"   Model A     : {settings['model_a']}")
    print(f"   Model B     : {settings['model_b']}")
    print(f"   Synthese    : {settings['synthesis_model']}")
    print(f"   Temperature : {settings['temperature']}")
    print(f"   Techniques  : {len(settings['techniques'])} actives")
    print(f"   Internet    : {inet}   Web enrichment : {web_st}   Streaming : {stream_st}")
    print("-" * 62)


def print_menu():
    print()
    print("  1.  Generation simple        (1 modele, streaming)")
    print("  2.  Generation parallele      (2 modeles, split screen)")
    print("  3.  Pipeline complet          (parallele + synthese)")
    print("  4.  Synthese de 2 fichiers")
    print()
    print("  5.  Configurer les modeles")
    print("  6.  Configurer les techniques")
    print("  7.  Voir les techniques disponibles")
    print("  8.  Parametres avances        (temperature, timeout, url, web, stream)")
    print()
    print("  9.  Voir la memoire")
    print("  10. Effacer la memoire")
    print()
    print("  0.  Quitter")
    print()


def ask_task_and_topics() -> Tuple[str, str]:
    print()
    task = input("  Decris ta tache:\n  > ").strip()
    if not task:
        print("  [!] La tache ne peut pas etre vide.")
        return "", ""
    topics_raw = input("  Topics (separes par des virgules, ou ENTREE pour aucun):\n  > ").strip()
    return task, topics_raw


def menu_generate(settings: dict):
    task, topics_raw = ask_task_and_topics()
    if not task:
        return
    model = pick_model_interactive("Modele de generation", settings["model_a"])
    use_web = settings.get("use_web", True)
    do_stream = settings.get("stream", True) and sys.stdout.isatty()

    if use_web and check_internet():
        print("\n  Recherche web en cours ...")
    print(f"  Lancement generation avec {model} ...")
    if do_stream:
        print(f"\n  --- {model} : streaming ---\n")

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
        )
        if do_stream:
            print("\n")
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        out_file = OUTPUT_DIR / f"{session_id}_{model.replace(':', '_')}.md"
        out_file.write_text(result, encoding="utf-8")
        print(f"\n  Manifeste sauvegarde : {out_file}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERREUR] {e}")


def menu_parallel(settings: dict):
    task, topics_raw = ask_task_and_topics()
    if not task:
        return
    model_a = pick_model_interactive("Modele A", settings["model_a"])
    model_b = pick_model_interactive("Modele B", settings["model_b"])
    use_web = settings.get("use_web", True)
    do_stream = settings.get("stream", True) and sys.stdout.isatty()

    if use_web and check_internet():
        print("\n  Recherche web en cours ...")
    print(f"  Lancement parallele {model_a} + {model_b} ...")
    if do_stream:
        print("  Split screen actif. Ctrl+C pour interrompre.\n")
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
        print(f"\n  Manifeste A : {fa}")
        print(f"  Manifeste B : {fb}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERREUR] {e}")


def menu_full(settings: dict):
    task, topics_raw = ask_task_and_topics()
    if not task:
        return
    model_a = pick_model_interactive("Modele A", settings["model_a"])
    model_b = pick_model_interactive("Modele B", settings["model_b"])
    synth = pick_model_interactive("Modele de synthese", settings["synthesis_model"])
    use_web = settings.get("use_web", True)
    do_stream = settings.get("stream", True) and sys.stdout.isatty()

    if use_web and check_internet():
        print("\n  Recherche web en cours ...")
    print(f"  Pipeline complet : {model_a} + {model_b} -> synthese {synth} ...")
    if do_stream:
        print("  Phase 1 : split screen parallele. Phase 2 : synthese streaming.\n")
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
        )
        print(f"\n  Manifeste A  : {fa}")
        print(f"  Manifeste B  : {fb}")
        print(f"  Synthese     : {fs}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERREUR] {e}")


def menu_synthesis(settings: dict):
    print()
    existing = sorted(OUTPUT_DIR.glob("*.md"))
    if not existing:
        print("  Aucun fichier dans outputs/. Lance d'abord une generation.")
        return
    print("  Fichiers disponibles dans outputs/ :")
    for i, f in enumerate(existing, 1):
        print(f"    {i:3d}. {f.name}")
    print()
    try:
        idx_a = int(input("  Numero du fichier A : ").strip()) - 1
        idx_b = int(input("  Numero du fichier B : ").strip()) - 1
        file_a = existing[idx_a]
        file_b = existing[idx_b]
    except (ValueError, IndexError):
        print("  [!] Selection invalide.")
        return
    task = input("  Tache d'origine (description courte) :\n  > ").strip()
    if not task:
        task = "(non fournie)"
    synth_model = pick_model_interactive("Modele de synthese", settings["synthesis_model"])
    print(f"\n  Synthese de {file_a.name} + {file_b.name} avec {synth_model} ...")
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
        )
        print(f"\n  Synthese sauvegardee : {out_path}")
    except (ValueError, RuntimeError, TimeoutError) as e:
        print(f"\n  [ERREUR] {e}")


def menu_configure_models(settings: dict):
    print()
    print("  -- Configuration des modeles par defaut --")
    print(f"  Actuels : A={settings['model_a']}  B={settings['model_b']}  Synth={settings['synthesis_model']}")
    settings["model_a"] = pick_model_interactive("Modele A (generation / simple)", settings["model_a"])
    settings["model_b"] = pick_model_interactive("Modele B (parallele)", settings["model_b"])
    settings["synthesis_model"] = pick_model_interactive("Modele de synthese", settings["synthesis_model"])
    save_settings(settings)
    print("\n  Modeles sauvegardes.")


def menu_configure_techniques(settings: dict):
    print()
    print("  -- Configuration des techniques --")
    current = ",".join(str(t) for t in settings["techniques"])
    print(f"  Actives : {current}")
    print()
    print("  Exemples de saisie :")
    print("    1,5,8,10,25     ->  techniques specifiques")
    print("    1-20             ->  plage")
    print("    1-10,25,40-50    ->  combinaison")
    print("    all              ->  toutes (1-100)")
    print("    default          ->  ensemble par defaut")
    print()
    raw = input("  Techniques : ").strip()
    if not raw:
        return
    if raw.lower() == "all":
        settings["techniques"] = list(range(1, 101))
    elif raw.lower() == "default":
        settings["techniques"] = list(DEFAULT_TECHNIQUES)
    else:
        settings["techniques"] = parse_techniques(raw)
    save_settings(settings)
    print(f"\n  {len(settings['techniques'])} techniques actives.")


def menu_list_techniques():
    print()
    print("  Techniques de Prompt Engineering disponibles :")
    print("  " + "-" * 58)
    for tid in sorted(TECHNIQUES_DB.keys()):
        tech = TECHNIQUES_DB[tid]
        print(f"  {tid:3d}. {tech['title']}")
        print(f"       {tech['description']}")
    print()
    input("  Appuie sur ENTREE pour revenir au menu...")


def prompt_bool(label: str, default: bool) -> bool:
    dstr = "oui" if default else "non"
    val = input(f"  {label} [{dstr}] (oui/non): ").strip().lower()
    if not val:
        return default
    return val in ("oui", "o", "yes", "y", "1", "true")


def menu_advanced(settings: dict):
    print()
    print("  -- Parametres avances --")
    settings["temperature"] = prompt_float("Temperature (0.0 - 1.0)", settings["temperature"])
    settings["timeout"] = prompt_int("Timeout par appel (secondes)", settings["timeout"])
    settings["ollama_url"] = prompt_input("URL Ollama", settings["ollama_url"])
    settings["use_web"] = prompt_bool("Enrichissement web automatique", settings.get("use_web", True))
    settings["stream"] = prompt_bool("Streaming temps reel dans le terminal", settings.get("stream", True))
    save_settings(settings)
    print("\n  Parametres sauvegardes.")


def interactive():
    settings = load_settings()
    ensure_ollama_ready()

    while True:
        clear_screen()
        print_banner(settings)
        print_menu()

        choice = input("  Choix > ").strip()

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
            continue
        elif choice == "8":
            menu_advanced(settings)
        elif choice == "9":
            print()
            print(view_memory())
        elif choice == "10":
            clear_memory()
            print("\n  Memoire effacee.")
        elif choice in ("0", "q", "quit", "exit"):
            print("\n  A bientot.\n")
            break
        else:
            print("\n  [!] Choix invalide.")

        if choice not in ("0", "q", "quit", "exit"):
            print()
            input("  Appuie sur ENTREE pour revenir au menu...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        interactive()
