# Wild_Root_Prompt Examples

Runnable demonstrations of Wild_Root_Prompt's CLI, REST API, and configuration. All
`.sh` files are meant to be read first, then run selectively — they are not a
single pipeline. Requires Ollama running locally (`ollama serve`) unless a
command explicitly targets an alternate backend.

| File | What it shows |
|---|---|
| [`cli_basics.sh`](cli_basics.sh) | The three core pipelines: `generate`, `parallel`, `full`, plus memory and technique listing |
| [`cli_advanced_features.sh`](cli_advanced_features.sh) | Technique bundles/random selection, draft mode, offline mode, PII redaction, fast preprocessing, deep research, result caching |
| [`rest_api.sh`](rest_api.sh) | Driving the web UI's REST endpoints directly with `curl` — useful for scripting or integrating Wild_Root_Prompt into another tool |
| [`alternate_backend.md`](alternate_backend.md) | Pointing Wild_Root_Prompt at LM Studio / text-generation-webui / GPT4All instead of Ollama |

Run any script with `bash examples/cli_basics.sh` from the repo root, or copy
individual commands out — they're deliberately commented so you can read them
as documentation.
