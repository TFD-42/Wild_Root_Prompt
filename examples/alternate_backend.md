# Using Wild_Root_Prompt with LM Studio / text-generation-webui / GPT4All

Wild_Root_Prompt defaults to Ollama, but also speaks the OpenAI-compatible
completions API that LM Studio, text-generation-webui (via its OpenAI
extension), and GPT4All's server mode all expose. One adapter covers all
three since they share the same wire format.

**Note:** for security (SSRF prevention), the backend URL must resolve to
`localhost`/`127.0.0.1` — run the server on the same machine as Wild_Root_Prompt.

## LM Studio

1. In LM Studio, load a model and start the local server (default port `1234`).
2. Run Wild_Root_Prompt against it:

```bash
python3 prompt_expert_enhance.py generate "explain quicksort" \
  --backend openai_compatible \
  --ollama-url http://localhost:1234/v1/completions \
  --model <the model name shown in LM Studio's server tab>
```

## text-generation-webui

1. Enable the `openai` extension and start the server (default port `5000`).
2. Point Wild_Root_Prompt at either its completions or chat endpoint:

```bash
python3 prompt_expert_enhance.py generate "explain quicksort" \
  --backend openai_compatible \
  --ollama-url http://localhost:5000/v1/chat/completions \
  --model <your loaded model>
```

## GPT4All (server mode)

Same pattern — start GPT4All's local API server, then point `--ollama-url`
at its `/v1/completions` (or `/v1/chat/completions`) endpoint with
`--backend openai_compatible`.

## Making it the default

Instead of passing `--backend`/`--ollama-url` on every command, set them
once via the interactive menu (`python3 prompt_expert_enhance.py` → Advanced
settings → Backend), or launch the web UI (`prompt_expert_enhance.py web`)
after setting them once in the interactive menu — the web server picks up
the same `backend_type`/`ollama_url` from `settings.json` at startup.

## What still assumes Ollama

- `ensure_ollama_ready()` (auto-install/start prompts) only runs for the
  `ollama` backend — for other backends, start/manage the server yourself
  through its own UI.
- Model *pulling* (`ollama pull`) has no equivalent — install/load models
  through LM Studio's/text-generation-webui's/GPT4All's own interface.
- `/api/models` model listing works against any backend (it calls
  `/v1/models` for OpenAI-compatible servers), but returned entries won't
  have file size/last-modified info the way Ollama's `/api/tags` provides.
