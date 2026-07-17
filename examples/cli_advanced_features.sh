#!/usr/bin/env bash
# Prompturgy — advanced/newer CLI features.
# Run from the repo root: bash examples/cli_advanced_features.sh
# Requires: ollama serve running, at least one model pulled.
set -e
cd "$(dirname "$0")/.."
MODEL="llama3.2:3b"

echo "=== Technique bundles: apply a pre-configured set for a task type ==="
echo "    (see prompt_expert_methodology.json's quick_reference for the full list)"
python3 prompt_expert_enhance.py generate \
  "write a production-grade JSON parser" \
  --model "$MODEL" --mode quick --techniques "bundle:Generation de code robuste"

echo
echo "=== Random technique subset: for creative exploration ==="
python3 prompt_expert_enhance.py generate \
  "brainstorm unconventional uses for a household drone" \
  --model "$MODEL" --mode quick --techniques "random:6"

echo
echo "=== Auto-recommend techniques from the task's own content ==="
python3 prompt_expert_enhance.py generate \
  "audit this codebase for security vulnerabilities" \
  --model "$MODEL" --mode quick --recommend-techniques

echo
echo "=== Draft mode: only sections 1-2 of the full manifest, for fast iteration ==="
python3 prompt_expert_enhance.py generate \
  "design a caching layer for a read-heavy API" \
  --model "$MODEL" --mode full --draft

echo
echo "=== Offline mode: skip all web enrichment and connectivity checks ==="
python3 prompt_expert_enhance.py generate \
  "explain the CAP theorem" \
  --model "$MODEL" --mode quick --offline

echo
echo "=== Fast preprocessing: regex-only cleanup, no extra Ollama call ==="
python3 prompt_expert_enhance.py generate \
  "explain  how   dns  resolution works,step by step" \
  --model "$MODEL" --mode quick --fast-preprocess

echo
echo "=== PII anonymization: redact personal info before it reaches any model ==="
python3 prompt_expert_enhance.py generate \
  "My name is Jane Doe, my email is jane@example.com — write me a cover letter" \
  --model "$MODEL" --mode quick --anonymize --no-preprocess

echo
echo "=== Result caching: identical requests are served instantly from cache/ ==="
echo "    (run the same command twice — the second run skips the Ollama call entirely)"
time python3 prompt_expert_enhance.py generate "what is a monad" --model "$MODEL" --mode quick > /dev/null
time python3 prompt_expert_enhance.py generate "what is a monad" --model "$MODEL" --mode quick > /dev/null
echo "    (add --no-cache to force a fresh call even for an identical prior request)"

echo
echo "=== Deep research: search, review candidates, manually pick sources (interactive) ==="
echo "    python3 prompt_expert_enhance.py generate \"latest trends in edge computing\" --model $MODEL --deep-research"
echo "    (not run automatically here — it prompts for terminal input)"
