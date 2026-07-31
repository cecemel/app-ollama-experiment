# app-ollama-experiment

Local AI agents. Default model `llama3.2:3b` (tool-calling capable).

- `opencode` - coding agent ([opencode](https://opencode.ai/))
- `opencode-light` - stripped opencode for small/local models. See `config/opencode-light/`
- `agent` - chat agent that can reach the web. See `config/agent/`
- `llama-prism` - PrismML llama.cpp fork runtime (loads group-128 GGUFs Ollama can't). See `config/llama-prism/`
- `ollama-local` - local [Ollama](https://ollama.ai/) model

## Getting started

```
drc up -d
drc logs -f ollama-local
```

All overrides go in `docker-compose.override.yml` (gitignored, stays local). Example - mount your own repos:

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
drc exec opencode opencode run --model ollama-local/llama3.2:3b "..."
drc exec opencode opencode run --model ollama-cloud/qwen3-coder:480b "..."
drc exec opencode opencode run --model llama-prism/bonsai-27b-1bit "..."
```

## Coding agent (opencode-light)

```
drc exec opencode-light opencode
```

Trimmed for small/local models. Same env knobs as `opencode`. See `config/opencode-light/` for what's stripped.

## Host localhost gateway (localhost-gateway provider)

`opencode` and `opencode-light` ship a `localhost-gateway` provider that reaches
services running on the **host's** localhost from inside the container. It uses
`host` (mapped to `host-gateway` via `extra_hosts` in `docker-compose.yml`), so it
works on Linux + Docker Desktop with no host-side setup. The base URL/port is baked
into the image at `config/opencode*/opencode.base.json` (default `http://host:8892/v1`) -
change it there and rebuild if you need a different port.

Register the host-side models in `docker-compose.override.yml`:

```yaml
services:
  opencode:
    environment:
      LOCALHOST_GATEWAY_MODELS: |
        {
          "my-local-model": { "tools": true }
        }
  opencode-light:
    environment:
      LOCALHOST_GATEWAY_MODELS: |
        {
          "my-local-model": { "tools": true }
        }
```

Then use it like any other provider:

```
drc exec opencode opencode run --model localhost-gateway/my-local-model "..."
```

The host service must bind on `0.0.0.0` (or `host`), not just `127.0.0.1` - Docker
reaches it via the host's bridge gateway IP, which a loopback-only bind won't
accept. The chat-log proxy (when `OPENCODE_LOG_CHAT=true`) routes this provider
under the `/gateway` prefix.

## Connected agent

```
drc exec agent run
```

Type `exit` or `quit` to stop.

## llama-prism

`llama-prism` runs [PrismML's llama.cpp fork](https://github.com/PrismML-Eng/llama.cpp) and serves an OpenAI-compatible `/v1` endpoint on port 8080. Downloads the GGUF on first boot (cached under `./data/llama-prism/`). See `config/llama-prism/start.sh` for all env knobs.

Default: 1-bit Bonsai 27B (`prism-ml/Bonsai-27B-gguf:Q1_0`, ~3.8GB). Switch to ternary (~7GB) in `docker-compose.override.yml`:

```yaml
services:
  llama-prism:
    environment:
      PRISM_MODEL: "prism-ml/Ternary-Bonsai-27B-gguf:Q2_0"
      LLAMA_ALIAS: "bonsai-27b-ternary"
  opencode:
    environment:
      PRISM_MODELS: |
        { "bonsai-27b-ternary": { "tools": true } }
```

### Build backend

`BACKEND` build arg in `docker-compose.yml` picks CPU or GPU. Default is `cpu`. Override it in `docker-compose.override.yml`:

```yaml
services:
  llama-prism:
    build:
      args:
        BACKEND: "vulkan"
```

```
drc build llama-prism
```

Options: `cpu`, `cuda-12.8`, `cuda-12.4`, `vulkan`, `rocm-7.2`. See `config/llama-prism/Dockerfile`.

GPU backends need device passthrough at runtime - see `docker-compose.override.yml`.

### NVIDIA GPU via CUDA

Use `BACKEND=cuda-12.8` (or `cuda-12.4`). The CUDA build starts from the matching
`nvidia/cuda` runtime image so the prebuilt `llama-server` can find `libcublas.so.12`
and friends at startup.

**Host requirements (one-time):**
- NVIDIA driver: >= 550.x for CUDA 12.4, >= 570.x for CUDA 12.8 (`nvidia-smi` shows
  the max CUDA version your driver supports)
- `nvidia-container-toolkit` installed - without it Docker can't pass the GPU +
  driver libs into the container

In `docker-compose.override.yml`:

```yaml
services:
  llama-prism:
    build:
      args:
        BACKEND: "cuda-12.8"      # or cuda-12.4
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      LLAMA_NGL: "99"
```

```
drc build llama-prism
drc up -d llama-prism
drc exec llama-prism nvidia-smi
```

### AMD iGPU (Phoenix3 / Radeon 780M) via Vulkan

Use `BACKEND=vulkan` (ROCm doesn't target iGPUs). In `docker-compose.override.yml`:

```yaml
services:
  llama-prism:
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
drc build llama-prism
drc up -d llama-prism
drc exec llama-prism vulkaninfo --summary
```

### Tool calling

Requires `--jinja` (on by default, `LLAMA_JINJA=1`). See `config/llama-prism/start.sh`. Allowed tools are set in `config/opencode*/opencode.base.json`. Debug via `OPENCODE_LOG_CHAT=true`.

## Accessing the raw model

```
drc exec ollama-local ollama run llama3.2:3b
```

## Choosing a model

Browse https://ollama.ai/library, then set `MODEL` in `docker-compose.yml`.