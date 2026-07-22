# app-ollama-experiment

Local AI agents on top of [Ollama](https://ollama.ai/). Default model `llama3.2:3b` (tool-calling capable).

- `opencode` - coding agent ([opencode](https://opencode.ai/))
- `opencode-light` - stripped opencode for small/local models. See `config/opencode-light/`
- `agent` - chat agent that can reach the web. See `config/agent/`
- `huggingface-local` - local HF runtime (PrismML llama.cpp fork). See `config/huggingface-local/`
- `ollama` - local Ollama model

## Getting started

```
drc up -d
drc logs -f ollama
```

Mount your own repos via a `docker-compose.override.yml` (gitignored):

```yaml
services:
  opencode:
    volumes:
      - /path/to/your/repo:/workspace/repo
```

## Coding agent (opencode)

```
drc exec opencode opencode
```

Config baked in at `config/opencode/opencode.base.json`. Knobs in `docker-compose.yml`: `OLLAMA_API_KEY`, `OLLAMA_CLOUD_MODELS`. Switch model per run:

```
drc exec opencode opencode run --model ollama/llama3.2:3b "..."
drc exec opencode opencode run --model ollama-cloud/qwen3-coder:480b "..."
drc exec opencode opencode run --model huggingface-local/bonsai-27b-1bit "..."
```

## Coding agent (opencode-light)

```
drc exec opencode-light opencode
```

Trimmed for small/local models. Same env knobs as `opencode`. See `config/opencode-light/` for what's stripped.

## Connected agent

```
drc exec agent run
```

Type `exit` or `quit` to stop.

## Local HF runtime

`huggingface-local` runs [PrismML's llama.cpp fork](https://github.com/PrismML-Eng/llama.cpp) and serves an OpenAI-compatible `/v1` endpoint on port 8080. Downloads the GGUF on first boot (cached under `./data/huggingface-local/`). See `config/huggingface-local/start.sh` for all env knobs.

Default: 1-bit Bonsai 27B (`prism-ml/Bonsai-27B-gguf:Q1_0`, ~3.8GB). Switch to ternary (~7GB):

```yaml
services:
  huggingface-local:
    environment:
      HF_MODEL: "prism-ml/Ternary-Bonsai-27B-gguf:Q2_0"
      LLAMA_ALIAS: "bonsai-27b-ternary"
  opencode:
    environment:
      HF_MODELS: |
        { "bonsai-27b-ternary": { "tools": true } }
```

### Build backend

`BACKEND` build arg in `docker-compose.yml` picks CPU or GPU. Default is `cpu`. To build for a GPU, override it in `docker-compose.override.yml` (gitignored, so it stays local):

```yaml
services:
  huggingface-local:
    build:
      args:
        BACKEND: "vulkan"
```

```
drc build huggingface-local
```

Options: `cpu`, `cuda-12.8`, `cuda-12.4`, `vulkan`, `rocm-7.2`. See `config/huggingface-local/Dockerfile`.

GPU backends need device passthrough at runtime - see `docker-compose.override.yml`.

### AMD iGPU (Phoenix3 / Radeon 780M) via Vulkan

Use `BACKEND=vulkan` (ROCm doesn't target iGPUs). In `docker-compose.override.yml`:

```yaml
services:
  huggingface-local:
    build:
      args:
        BACKEND: "vulkan"
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - video
    environment:
      LLAMA_NGL: "99"
```

```
drc build huggingface-local
drc up -d huggingface-local
drc exec huggingface-local vulkaninfo --summary
```

### Tool calling

Requires `--jinja` (on by default, `LLAMA_JINJA=1`). See `config/huggingface-local/start.sh`. Allowed tools are set in `config/opencode*/opencode.base.json`. Debug via `OPENCODE_LOG_CHAT=true`.

## Accessing the raw model

```
drc exec ollama ollama run llama3.2:3b
```

## Choosing a model

Browse https://ollama.ai/library, then set `MODEL` in `docker-compose.yml`.