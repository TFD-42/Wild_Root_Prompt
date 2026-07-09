#!/usr/bin/env python3
"""
Pro-Prompt Web UI — Local web interface for novice users.
Served at http://localhost:7860 — no external connections.
"""

import json
import queue
import sys
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from flask import Flask, Response, jsonify, request, stream_with_context
except ImportError:
    print("\n  [!] Flask not installed. Run:  pip install flask")
    sys.exit(1)

# Import generation functions from main module
sys.path.insert(0, str(BASE_DIR))
from prompt_expert_enhance import (
    DEFAULT_MODEL_A, DEFAULT_MODEL_B, DEFAULT_SYNTH_MODEL,
    DEFAULT_TECHNIQUES, OLLAMA_URL,
    generate_multi_topics, generate_parallel_both, run_full_pipeline,
    pre_process_input, list_local_models, sanitize_input,
    load_settings, save_settings, PRE_PROCESSOR_TIMEOUT,
    is_ollama_running, ensure_ollama_ready,
)

app = Flask(__name__, static_folder=None)
app.config["SECRET_KEY"] = __import__("secrets").token_hex(32)  # random per-run, never stored

# Suppress Werkzeug request logs — no IPs, no paths printed to terminal
import logging as _logging
_logging.getLogger("werkzeug").setLevel(_logging.ERROR)

# ── Embedded HTML ────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pro-Prompt — Local AI</title>
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #22263a;
  --border: #2e3250;
  --accent: #6c7fff;
  --accent2: #a78bfa;
  --green: #4ade80;
  --yellow: #fbbf24;
  --red: #f87171;
  --text: #e2e8f0;
  --muted: #8892a4;
  --radius: 10px;
  --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
  --mono: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font); background: var(--bg); color: var(--text); min-height: 100vh; }

/* Layout */
.layout { display: grid; grid-template-columns: 420px 1fr; min-height: 100vh; }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }

/* Sidebar */
.sidebar {
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  height: 100vh; overflow-y: auto; position: sticky; top: 0;
}
.sidebar-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border);
}
.logo { font-size: 1.25rem; font-weight: 700; color: var(--accent); letter-spacing: -.5px; }
.logo span { color: var(--accent2); }
.tagline { font-size: .78rem; color: var(--muted); margin-top: 4px; }

.sidebar-body { padding: 20px; flex: 1; display: flex; flex-direction: column; gap: 18px; }

label { font-size: .8rem; color: var(--muted); display: block; margin-bottom: 6px; font-weight: 500; text-transform: uppercase; letter-spacing: .5px; }

textarea, select, input[type=range] {
  width: 100%; background: var(--surface2); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text); font-family: var(--font);
  font-size: .95rem; transition: border-color .15s;
}
textarea { padding: 12px; resize: vertical; min-height: 120px; line-height: 1.5; }
textarea:focus, select:focus { outline: none; border-color: var(--accent); }
select { padding: 10px 12px; cursor: pointer; }
select option { background: var(--surface2); }

.hint { font-size: .75rem; color: var(--muted); margin-top: 5px; line-height: 1.4; }

/* Metacommands chips */
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  padding: 4px 10px; border-radius: 20px; font-size: .75rem; cursor: pointer;
  background: var(--surface2); border: 1px solid var(--border); color: var(--muted);
  transition: all .15s; user-select: none;
}
.chip:hover { border-color: var(--accent); color: var(--accent); }
.chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }

/* Mode toggle */
.mode-toggle { display: flex; gap: 8px; }
.mode-btn {
  flex: 1; padding: 10px; border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--surface2); color: var(--muted); cursor: pointer; font-size: .85rem;
  text-align: center; transition: all .15s;
}
.mode-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }

/* PP toggle */
.toggle-row { display: flex; align-items: center; justify-content: space-between; }
.toggle { position: relative; display: inline-block; width: 40px; height: 22px; }
.toggle input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; inset: 0; background: var(--border); border-radius: 22px; cursor: pointer;
  transition: .2s;
}
.slider:before {
  content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px;
  background: white; border-radius: 50%; transition: .2s;
}
input:checked + .slider { background: var(--accent); }
input:checked + .slider:before { transform: translateX(18px); }

/* Model row */
.model-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

/* Run button */
.btn-run {
  width: 100%; padding: 14px; border-radius: var(--radius); border: none;
  background: var(--accent); color: white; font-size: 1rem; font-weight: 700;
  cursor: pointer; transition: all .15s; letter-spacing: .3px;
}
.btn-run:hover { background: #5a6ef0; transform: translateY(-1px); }
.btn-run:active { transform: translateY(0); }
.btn-run:disabled { background: var(--border); color: var(--muted); cursor: not-allowed; transform: none; }

.status-row { display: flex; align-items: center; gap: 8px; font-size: .8rem; color: var(--muted); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }
.dot.green { background: var(--green); }
.dot.red { background: var(--red); }

/* Main area */
.main { display: flex; flex-direction: column; }
.main-header { padding: 20px 28px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.main-header h2 { font-size: 1rem; font-weight: 600; color: var(--text); }
.tab-bar { display: flex; gap: 4px; }
.tab-btn {
  padding: 6px 14px; border-radius: 6px; border: none; background: transparent;
  color: var(--muted); cursor: pointer; font-size: .85rem; transition: all .15s;
}
.tab-btn.active { background: var(--surface2); color: var(--text); }

.output-area {
  flex: 1; padding: 24px 28px; overflow-y: auto;
  font-family: var(--mono); font-size: .875rem; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
}
.output-area.empty { font-family: var(--font); }

.placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 16px; color: var(--muted);
}
.placeholder .icon { font-size: 3rem; opacity: .3; }
.placeholder p { font-size: .9rem; text-align: center; max-width: 320px; line-height: 1.6; }

.pp-banner {
  margin: 0 28px 16px; padding: 12px 16px; border-radius: var(--radius);
  background: var(--surface2); border: 1px solid var(--border);
  font-size: .85rem; color: var(--muted);
  display: none;
}
.pp-banner strong { color: var(--accent2); }
.pp-banner .pp-text { margin-top: 8px; color: var(--text); font-family: var(--mono); font-size: .82rem; white-space: pre-wrap; }

/* Parallel panels */
.dual-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0 28px; }
.panel-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  overflow: hidden;
}
.panel-card .panel-header { padding: 10px 14px; background: var(--surface2); border-bottom: 1px solid var(--border); font-size: .8rem; font-weight: 600; color: var(--accent); }
.panel-card .panel-body { padding: 14px; font-family: var(--mono); font-size: .82rem; line-height: 1.6; white-space: pre-wrap; min-height: 200px; overflow-y: auto; max-height: 60vh; }

/* Progress */
.progress-bar { height: 3px; background: var(--border); position: relative; overflow: hidden; }
.progress-bar .fill { height: 100%; background: var(--accent); width: 0%; transition: width .3s; }
.progress-bar .indeterminate {
  height: 100%; background: var(--accent);
  animation: indeterminate 1.5s infinite;
  position: absolute; width: 30%;
}
@keyframes indeterminate {
  0% { left: -30%; } 100% { left: 100%; }
}

/* Save btn */
.btn-save {
  padding: 8px 16px; border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--surface2); color: var(--text); cursor: pointer; font-size: .82rem;
  transition: all .15s;
}
.btn-save:hover { border-color: var(--green); color: var(--green); }
</style>
</head>
<body>
<div class="layout">

<!-- ── SIDEBAR ─────────────────────────────── -->
<div class="sidebar">
  <div class="sidebar-header">
    <div class="logo">Pro<span>-Prompt</span></div>
    <div class="tagline">Local AI Prompt Enhancement &nbsp;·&nbsp; v2.3</div>
  </div>

  <div class="sidebar-body">

    <!-- Status -->
    <div class="status-row">
      <div class="dot" id="ollama-dot"></div>
      <span id="ollama-status">Checking Ollama...</span>
    </div>

    <!-- Prompt -->
    <div>
      <label>Your Prompt</label>
      <textarea id="prompt" placeholder="Describe what you need. Can be short or messy — the pre-processor will clean it up.&#10;&#10;Example: explain quantum computing to a 12 year old"></textarea>
      <div class="hint">Type your idea, task, or question. No need to be perfect — that's what Pro-Prompt is for.</div>
    </div>

    <!-- /slash metacommands -->
    <div>
      <label>Modifiers <span style="font-weight:400;text-transform:none;">(click to add)</span></label>
      <div class="chips" id="chips">
        <div class="chip" data-cmd="/expert">/expert</div>
        <div class="chip" data-cmd="/raisonnement">/reasoning</div>
        <div class="chip" data-cmd="/etapes">/steps</div>
        <div class="chip" data-cmd="/exemple">/examples</div>
        <div class="chip" data-cmd="/critique">/critique</div>
        <div class="chip" data-cmd="/json">/json</div>
        <div class="chip" data-cmd="/points">/bullet list</div>
        <div class="chip" data-cmd="/markdown">/markdown</div>
        <div class="chip" data-cmd="/resume">/summary</div>
        <div class="chip" data-cmd="/detaille">/detailed</div>
        <div class="chip" data-cmd="/sources">/sources</div>
        <div class="chip" data-cmd="/risques">/risks</div>
        <div class="chip" data-cmd="/comparatif">/compare</div>
        <div class="chip" data-cmd="/audit">/audit</div>
      </div>
    </div>

    <!-- Output mode -->
    <div>
      <label>Output Mode</label>
      <div class="mode-toggle">
        <div class="mode-btn active" data-mode="quick" id="mode-quick">
          ⚡ Quick<br><span style="font-size:.72rem;font-weight:400">Enhanced prompt, paste-ready</span>
        </div>
        <div class="mode-btn" data-mode="full" id="mode-full">
          📋 Full<br><span style="font-size:.72rem;font-weight:400">12-section expert manifest</span>
        </div>
      </div>
    </div>

    <!-- Pipeline -->
    <div>
      <label>Pipeline</label>
      <select id="pipeline">
        <option value="single">Single model</option>
        <option value="parallel" selected>2 models in parallel</option>
        <option value="full_pipeline">Full pipeline (parallel + synthesis)</option>
      </select>
    </div>

    <!-- Models -->
    <div>
      <label>Model(s)</label>
      <div class="model-row">
        <div>
          <label style="font-size:.72rem;">Model A</label>
          <select id="model-a" style="font-size:.82rem;"></select>
        </div>
        <div id="model-b-wrap">
          <label style="font-size:.72rem;">Model B</label>
          <select id="model-b" style="font-size:.82rem;"></select>
        </div>
      </div>
    </div>

    <!-- Pre-processor toggle -->
    <div>
      <div class="toggle-row">
        <label style="margin:0">Pre-processor <span style="font-weight:400;color:var(--accent2)">(auto-restructure input)</span></label>
        <label class="toggle">
          <input type="checkbox" id="use-pp" checked>
          <span class="slider"></span>
        </label>
      </div>
      <div class="hint" style="margin-top:6px">Ollama cleans and restructures your prompt before the main generation.</div>
    </div>

    <!-- Run -->
    <button class="btn-run" id="btn-run" onclick="runGeneration()">Generate ↗</button>

  </div><!-- /sidebar-body -->
</div><!-- /sidebar -->

<!-- ── MAIN ────────────────────────────────── -->
<div class="main">
  <div class="main-header">
    <h2 id="main-title">Output</h2>
    <div style="display:flex;gap:8px;align-items:center;">
      <button class="btn-save" id="btn-copy" onclick="copyOutput()" style="display:none">Copy</button>
      <button class="btn-save" id="btn-download" onclick="downloadOutput()" style="display:none">Download .md</button>
    </div>
  </div>

  <div class="progress-bar" id="progress-bar">
    <div class="indeterminate" id="progress-fill" style="display:none"></div>
  </div>

  <!-- PP banner -->
  <div class="pp-banner" id="pp-banner">
    <strong>Pre-processor restructured your prompt:</strong>
    <div class="pp-text" id="pp-text"></div>
  </div>

  <!-- Output: single / synthesis -->
  <div class="output-area empty" id="output-single">
    <div class="placeholder">
      <div class="icon">⚡</div>
      <p>Enter your prompt on the left and click <strong>Generate</strong>.<br>Your enhanced output will appear here.</p>
    </div>
  </div>

  <!-- Output: parallel panels -->
  <div id="output-parallel" style="display:none;padding-top:20px;">
    <div class="dual-panel">
      <div class="panel-card">
        <div class="panel-header" id="label-a">Model A</div>
        <div class="panel-body" id="panel-a"></div>
      </div>
      <div class="panel-card">
        <div class="panel-header" id="label-b">Model B</div>
        <div class="panel-body" id="panel-b"></div>
      </div>
    </div>
    <div style="padding:20px 28px 0;" id="synthesis-section" style="display:none">
      <div class="panel-card" style="margin-top:0">
        <div class="panel-header" style="color:var(--accent2)">Expert Synthesis</div>
        <div class="panel-body" id="panel-synth"></div>
      </div>
    </div>
  </div>

</div><!-- /main -->
</div><!-- /layout -->

<script>
const $ = id => document.getElementById(id)
let selectedMode = 'quick'
let activeChips = []
let lastOutput = ''
let isRunning = false

// ── Init ───────────────────────────────────────────────────────────────────

async function init() {
  checkOllama()
  loadModels()
  pipelineChange()
  setInterval(checkOllama, 10000)
}

async function checkOllama() {
  try {
    const r = await fetch('/api/status')
    const d = await r.json()
    $('ollama-dot').className = 'dot ' + (d.ollama ? 'green' : 'red')
    $('ollama-status').textContent = d.ollama ? 'Ollama running — ready' : 'Ollama not running — start it first'
  } catch { $('ollama-dot').className = 'dot red'; $('ollama-status').textContent = 'Server error' }
}

async function loadModels() {
  try {
    const r = await fetch('/api/models')
    const d = await r.json()
    const models = d.models || []
    ;['model-a', 'model-b'].forEach(id => {
      const sel = $(id)
      sel.innerHTML = ''
      if (!models.length) {
        sel.innerHTML = '<option value="">No models found</option>'
        return
      }
      models.forEach((m, i) => {
        const opt = document.createElement('option')
        opt.value = m.name; opt.textContent = m.name
        if (i === 0 && id === 'model-a') opt.selected = true
        if (i === 1 && id === 'model-b') opt.selected = true
        else if (i === 0 && id === 'model-b') opt.selected = true
        sel.appendChild(opt)
      })
    })
  } catch(e) { console.error(e) }
}

// ── Mode & pipeline ────────────────────────────────────────────────────────

document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'))
    btn.classList.add('active')
    selectedMode = btn.dataset.mode
  })
})

function pipelineChange() {
  const p = $('pipeline').value
  $('model-b-wrap').style.display = p === 'single' ? 'none' : ''
  $('synthesis-section').style.display = p === 'full_pipeline' ? '' : 'none'
}
$('pipeline').addEventListener('change', pipelineChange)

// ── Chips ──────────────────────────────────────────────────────────────────

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const cmd = chip.dataset.cmd
    if (chip.classList.contains('active')) {
      chip.classList.remove('active')
      activeChips = activeChips.filter(c => c !== cmd)
    } else {
      chip.classList.add('active')
      activeChips.push(cmd)
    }
  })
})

// ── Run ────────────────────────────────────────────────────────────────────

async function runGeneration() {
  if (isRunning) return
  const raw = $('prompt').value.trim()
  if (!raw) { alert('Please enter a prompt first.'); return }

  isRunning = true
  $('btn-run').disabled = true
  $('btn-run').textContent = 'Generating...'
  $('btn-copy').style.display = 'none'
  $('btn-download').style.display = 'none'
  $('pp-banner').style.display = 'none'
  $('progress-fill').style.display = 'block'

  const pipeline = $('pipeline').value
  const modelA = $('model-a').value
  const modelB = $('model-b').value
  const usePP = $('use-pp').checked

  // Build full prompt with chips
  const metaCmds = activeChips.join(' ')
  const task = metaCmds ? metaCmds + ' ' + raw : raw

  // Pre-processor (optional, quick client-side SSE)
  if (usePP) {
    await runPreprocessor(task, modelA)
  }

  const finalTask = usePP ? ($('pp-text').textContent || task) : task

  // Show correct panel
  if (pipeline === 'single') {
    showSingle()
    await streamSingle(finalTask, modelA)
  } else if (pipeline === 'parallel') {
    showParallel()
    await streamParallel(finalTask, modelA, modelB)
  } else {
    showParallel(true)
    await streamParallel(finalTask, modelA, modelB, true)
  }

  finishRun()
}

async function runPreprocessor(task, model) {
  try {
    const r = await fetch('/api/preprocess', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task, model})
    })
    const d = await r.json()
    if (d.result && d.result !== task) {
      $('pp-text').textContent = d.result
      $('pp-banner').style.display = 'block'
    }
  } catch(e) { /* silent fallback */ }
}

async function streamSingle(task, model) {
  $('output-single').innerHTML = ''
  $('output-single').classList.remove('empty')
  lastOutput = ''
  try {
    const r = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task, model, mode: selectedMode, pipeline: 'single'})
    })
    const reader = r.body.getReader()
    const dec = new TextDecoder()
    while (true) {
      const {done, value} = await reader.read()
      if (done) break
      const chunk = dec.decode(value)
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data:')) continue
        try {
          const d = JSON.parse(line.slice(5))
          if (d.token) { lastOutput += d.token; $('output-single').textContent = lastOutput }
        } catch {}
      }
    }
  } catch(e) { $('output-single').textContent = 'Error: ' + e.message }
}

async function streamParallel(task, modelA, modelB, withSynth = false) {
  $('label-a').textContent = modelA
  $('label-b').textContent = modelB
  $('panel-a').textContent = ''
  $('panel-b').textContent = ''
  $('panel-synth').textContent = ''
  lastOutput = ''

  let outA = '', outB = ''

  const streamPanel = async (panel, model, accumulator) => {
    try {
      const r = await fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task, model, mode: selectedMode, pipeline: 'single'})
      })
      const reader = r.body.getReader()
      const dec = new TextDecoder()
      while (true) {
        const {done, value} = await reader.read()
        if (done) break
        const chunk = dec.decode(value)
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data:')) continue
          try {
            const d = JSON.parse(line.slice(5))
            if (d.token) { accumulator[0] += d.token; panel.textContent = accumulator[0] }
          } catch {}
        }
      }
    } catch(e) { panel.textContent = 'Error: ' + e.message }
  }

  const accA = [''], accB = ['']
  await Promise.all([
    streamPanel($('panel-a'), modelA, accA),
    streamPanel($('panel-b'), modelB, accB)
  ])
  outA = accA[0]; outB = accB[0]
  lastOutput = `# Model A (${modelA})\n\n${outA}\n\n---\n\n# Model B (${modelB})\n\n${outB}`

  if (withSynth && outA && outB) {
    $('synthesis-section').style.display = ''
    $('panel-synth').textContent = 'Synthesizing...'
    try {
      const r = await fetch('/api/synthesize', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task, manifest_a: outA, manifest_b: outB, model: $('model-a').value})
      })
      const reader = r.body.getReader()
      const dec = new TextDecoder()
      let synth = ''
      while (true) {
        const {done, value} = await reader.read()
        if (done) break
        const chunk = dec.decode(value)
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data:')) continue
          try {
            const d = JSON.parse(line.slice(5))
            if (d.token) { synth += d.token; $('panel-synth').textContent = synth }
          } catch {}
        }
      }
      lastOutput += `\n\n---\n\n# Synthesis\n\n${synth}`
    } catch(e) { $('panel-synth').textContent = 'Synthesis error: ' + e.message }
  }
}

function showSingle() {
  $('output-single').style.display = ''
  $('output-parallel').style.display = 'none'
}
function showParallel(withSynth = false) {
  $('output-single').style.display = 'none'
  $('output-parallel').style.display = ''
  $('synthesis-section').style.display = withSynth ? '' : 'none'
}

function finishRun() {
  isRunning = false
  $('btn-run').disabled = false
  $('btn-run').textContent = 'Generate ↗'
  $('progress-fill').style.display = 'none'
  if (lastOutput) {
    $('btn-copy').style.display = ''
    $('btn-download').style.display = ''
  }
}

function copyOutput() {
  navigator.clipboard.writeText(lastOutput).then(() => {
    $('btn-copy').textContent = 'Copied ✓'
    setTimeout(() => { $('btn-copy').textContent = 'Copy' }, 2000)
  })
}

function downloadOutput() {
  const blob = new Blob([lastOutput], {type: 'text/markdown'})
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'pro-prompt-output.md'
  a.click()
}

init()
</script>
</body>
</html>
"""

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/status")
def api_status():
    return jsonify({"ollama": is_ollama_running()})


@app.route("/api/models")
def api_models():
    try:
        models = list_local_models()
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})


@app.route("/api/preprocess", methods=["POST"])
def api_preprocess():
    data = request.get_json(force=True, silent=True) or {}
    task = sanitize_input(data.get("task", ""), "text")
    model = sanitize_input(data.get("model", DEFAULT_MODEL_A), "model")
    settings = load_settings()
    ollama_url = settings.get("ollama_url", OLLAMA_URL)
    if not task:
        return jsonify({"result": ""})
    result = pre_process_input(task, model, ollama_url, timeout=PRE_PROCESSOR_TIMEOUT)
    return jsonify({"result": result})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True, silent=True) or {}
    task = sanitize_input(data.get("task", ""), "text")
    model = sanitize_input(data.get("model", DEFAULT_MODEL_A), "model")
    mode = data.get("mode", "full") if data.get("mode") in ("quick", "full") else "full"
    settings = load_settings()

    if not task:
        return jsonify({"error": "Empty task"}), 400

    token_queue: queue.Queue = queue.Queue()

    def stream_cb(token: str):
        token_queue.put(token)

    def run():
        try:
            generate_multi_topics(
                model=model,
                user_input=task,
                topics_raw="",
                temperature=settings.get("temperature", 0.3),
                use_memory=True,
                ollama_url=settings.get("ollama_url", OLLAMA_URL),
                timeout=settings.get("timeout", 600),
                techniques=settings.get("techniques", list(DEFAULT_TECHNIQUES)),
                use_web=settings.get("use_web", True),
                stream_callback=stream_cb,
                mode=mode,
            )
        except Exception as e:
            token_queue.put(f"\n[ERROR] {e}")
        finally:
            token_queue.put(None)  # sentinel

    t = threading.Thread(target=run, daemon=True)
    t.start()

    def generate_sse():
        while True:
            token = token_queue.get()
            if token is None:
                yield "data: {\"done\": true}\n\n"
                break
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n"

    return Response(
        stream_with_context(generate_sse()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/synthesize", methods=["POST"])
def api_synthesize():
    data = request.get_json(force=True, silent=True) or {}
    task = sanitize_input(data.get("task", ""), "text")
    manifest_a = sanitize_input(data.get("manifest_a", ""), "text")
    manifest_b = sanitize_input(data.get("manifest_b", ""), "text")
    model = sanitize_input(data.get("model", DEFAULT_SYNTH_MODEL), "model")
    settings = load_settings()

    if not manifest_a or not manifest_b:
        return jsonify({"error": "Both manifests required"}), 400

    token_queue: queue.Queue = queue.Queue()

    def stream_cb(token: str):
        token_queue.put(token)

    def run():
        try:
            from prompt_expert_enhance import run_synthesis
            run_synthesis(
                user_input=task or "synthesis",
                manifest_a=manifest_a,
                manifest_b=manifest_b,
                temperature=settings.get("temperature", 0.3),
                use_memory=False,
                ollama_url=settings.get("ollama_url", OLLAMA_URL),
                timeout=settings.get("timeout", 1200),
                synthesis_model=model,
                techniques=settings.get("techniques", list(DEFAULT_TECHNIQUES)),
                stream=True,
                stream_callback=stream_cb,
            )
        except Exception as e:
            token_queue.put(f"\n[ERROR] {e}")
        finally:
            token_queue.put(None)

    threading.Thread(target=run, daemon=True).start()

    def generate_sse():
        while True:
            token = token_queue.get()
            if token is None:
                yield "data: {\"done\": true}\n\n"
                break
            yield f"data: {json.dumps({'token': token})}\n\n"

    return Response(
        stream_with_context(generate_sse()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Launcher ─────────────────────────────────────────────────────────────────

def run_web_server(port: int = 7860, open_browser: bool = True):
    print(f"\n  Pro-Prompt Web UI")
    print(f"  ─────────────────────────────────────")
    print(f"  URL   : http://localhost:{port}")
    print(f"  Stop  : Ctrl+C")
    print()

    if open_browser:
        def _open():
            import time as _time
            _time.sleep(1.2)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open, daemon=True).start()

    try:
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)
    except OSError as e:
        print(f"\n  [ERROR] Could not start server on port {port}: {e}")
        print(f"  Try:  python prompt_expert_enhance.py web --port 7861")
        sys.exit(1)


if __name__ == "__main__":
    run_web_server()
