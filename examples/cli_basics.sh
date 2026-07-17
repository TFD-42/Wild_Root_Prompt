#!/usr/bin/env bash
# Wild_Root_Prompt — CLI basics.
# Run from the repo root: bash examples/cli_basics.sh
# Requires: ollama serve running, at least one model pulled (e.g. `ollama pull llama3.2:3b`).
set -e
cd "$(dirname "$0")/.."

echo "=== generate: single model, quick mode (fast, paste-ready prompt) ==="
python3 prompt_expert_enhance.py generate \
  "write a Python function that validates an email address" \
  --model llama3.2:3b --mode quick

echo
echo "=== generate: single model, full mode (12-section expert manifest) ==="
python3 prompt_expert_enhance.py generate \
  "design a rate limiter for a public API" \
  --model llama3.2:3b --mode full --output /tmp/rate_limiter_manifest.md
echo "Saved to /tmp/rate_limiter_manifest.md"

echo
echo "=== parallel: two models generate independently, compare their output ==="
python3 prompt_expert_enhance.py parallel \
  "explain how a B-tree index works" \
  --model-a llama3.2:3b --model-b llama3.2:3b --mode quick

echo
echo "=== full: parallel generation, then a synthesis pass merges both into one ==="
python3 prompt_expert_enhance.py full \
  "plan a migration from REST to GraphQL" \
  --model-a llama3.2:3b --model-b llama3.2:3b --mode quick

echo
echo "=== memory: view/clear the rolling session history used for continuity ==="
python3 prompt_expert_enhance.py memory view
# python3 prompt_expert_enhance.py memory clear   # uncomment to wipe it

echo
echo "=== list all 173 prompt-engineering techniques, grouped by category ==="
python3 prompt_expert_enhance.py generate "placeholder" --list-techniques | head -30

echo
echo "=== templates: start from a predefined task instead of writing one from scratch ==="
python3 prompt_expert_enhance.py templates list
python3 prompt_expert_enhance.py generate "distributed systems" --template learning_plan \
  --model llama3.2:3b --mode quick --no-preprocess
