#!/usr/bin/env bash
# Prompturgy — REST API usage via curl.
# Start the server first: python3 prompt_expert_enhance.py web --no-browser
# Then run: bash examples/rest_api.sh
# The server binds to 127.0.0.1 only — not reachable from other machines.
set -e
BASE="http://localhost:7860"

echo "=== GET /api/status — is Ollama reachable? ==="
curl -s "$BASE/api/status" | python3 -m json.tool

echo
echo "=== GET /api/models — list locally installed models ==="
curl -s "$BASE/api/models" | python3 -m json.tool

echo
echo "=== POST /api/preprocess — restructure a raw task before generation ==="
curl -s -X POST "$BASE/api/preprocess" \
  -H "Content-Type: application/json" \
  -d '{"task": "explain kubernetes to me simply", "model": "llama3.2:3b"}' \
  | python3 -m json.tool

echo
echo "=== POST /api/generate — streamed generation (Server-Sent Events) ==="
echo "    (this streams tokens; piping through 'head' just shows the first few lines)"
curl -s -N -X POST "$BASE/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"task": "explain the actor model", "model": "llama3.2:3b", "mode": "quick"}' \
  | head -20

echo
echo "(see web_server.py's HTML/JS for the full request/response shape used by the UI itself)"
