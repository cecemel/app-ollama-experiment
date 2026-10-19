# app-ollama-experiment

Local AI agents. Default model `ollama-cloud/glm-5.2` (tool-calling capable). `small_model` stays on `ollama-local/llama3.2:3b` for titles/summaries.

- `opencode` - coding agent ([opencode](https://opencode.ai/)), runs as a headless server on `:4096` so openchamber can drive it
- `opencode-light` - stripped opencode for small/local models. See `config/opencode-light/`
- `openchamber` - web UI for opencode ([openchamber](https://openchamber.dev/)). Connects to the `opencode` server. See `config/openchamber/`
- `openchamber-relay` - self-hosted [private relay](https://github.com/openchamber/openchamber-relay) so your paired devices reach openchamber from anywhere. See `config/openchamber-relay/`
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

`drc up -d opencode` runs opencode as a headless HTTP server on `:4096` (`opencode serve --hostname 0.0.0.0`). The port is not published; only other containers on the compose network (openchamber) reach it. Start an interactive TUI any time with:

```
drc exec opencode opencode
```

The TUI runs alongside the server without conflict. Config baked in at `config/opencode/opencode.base.json`. Knobs in `docker-compose.yml`: `OLLAMA_API_KEY`, `OLLAMA_CLOUD_MODELS`. Switch model per run:

```
drc exec opencode opencode run --model ollama-local/llama3.2:3b "..."
drc exec opencode opencode run --model ollama-cloud/qwen3-coder:480b "..."
drc exec opencode opencode run --model llama-prism/bonsai-27b-1bit "..."
```

### Agent instructions (AGENTS.md)

The gitignored `./config/opencode/AGENTS.md` is mounted read-only into the container at `/etc/opencode/AGENTS.md` from `docker-compose.override.yml` (this repo is public; personal rules don't ship in the image):

```yaml
services:
  opencode:
    volumes:
      - ./config/opencode/AGENTS.md:/etc/opencode/AGENTS.md:ro
```

At boot `start.sh` copies it to `/root/.config/opencode/AGENTS.md`, which opencode auto-discovers as global rules and applies to every session. Missing or empty source warns (but never crashes). Restart opencode to reload after edits.

## Coding agent (opencode-light)

```
drc exec opencode-light opencode
```

Trimmed for small/local models. Same env knobs as `opencode`. See `config/opencode-light/` for what's stripped.

## OpenChamber (web UI)

[OpenChamber](https://openchamber.dev/) is the visual workspace around opencode. The `openchamber` service runs the web app and connects to the `opencode` server over the compose network, so bring opencode up first:

```
drc up -d opencode
drc up -d openchamber
```

Open http://localhost:3000 and sign in with `OPENCHAMBER_UI_PASSWORD`. To pair a phone or reach it from outside your network, set `OPENCHAMBER_RELAY_URL` (see below) and pair a device in Settings -> Remote Instances.

What's constant (in `docker-compose.yml`): `OPENCODE_HOST=http://opencode:4096`, `OPENCODE_SKIP_START=true`, `OPENCHAMBER_HOST=0.0.0.0`, the web UI port `3000`, and a placeholder `OPENCHAMBER_UI_PASSWORD`.

What's deploy-specific (in `docker-compose.override.yml`): `OPENCHAMBER_RELAY_URL`, the public wss endpoint of your relay, and your real `OPENCHAMBER_UI_PASSWORD`:

```yaml
services:
  openchamber:
    environment:
      OPENCHAMBER_RELAY_URL: "wss://relay.example.com/ws"
      OPENCHAMBER_UI_PASSWORD: "your-secret"
```

openchamber does not run its own opencode (`OPENCODE_SKIP_START=true`); it drives the `opencode` service, so all providers, the chat-log proxy, `AGENTS.md`, and the custom tools stay single-sourced there.

## OpenChamber Relay (self-hosted)

Run the relay on a server so your paired devices reach openchamber from anywhere, without opening ports on the agent machine. Clone this repo on the server and:

```
drc up -d openchamber-relay
```

The image listens on `:80` inside the container (`EXPOSE 80`, `PORT=80`). The port is **not** published for you. Put your own TLS termination in front (Let's Encrypt / reverse proxy) and forward `wss://relay.example.com/ws` to the relay's port 80. Publish the port yourself, e.g. in `docker-compose.override.yml`:

```yaml
services:
  openchamber-relay:
    ports:
      - "80:80"
```

The relay is a stateless E2EE broker: it forwards already-encrypted frames between your openchamber instance and paired devices, stores no secrets, and needs none. Health check: `GET /health` returns `{"ok":true,"service":"openchamber-relay"}`. Optional usage accounting: set `RELAY_USAGE_DB=/data/usage.sqlite` and mount `./data/openchamber-relay:/data`.

Then point openchamber at it via `OPENCHAMBER_RELAY_URL` (see above). The same repo serves both roles: `drc up -d openchamber` on the agent machine, `drc up -d openchamber-relay` on the relay server.

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

## LOV vocabulary search (built-in tool)

`opencode` and `opencode-light` ship a `lov-sparql` custom tool. When the user
asks for RDF vocabularies / ontologies / schemas, the agent calls it **in
addition to** any web search. It queries the [LOV](https://lov.linkeddata.es/)
(Liked Open Vocabularies) SPARQL endpoint and returns matching vocabularies
(URI, prefix, title, description).

The tool is self-contained - it uses only the built-in `fetch`, so it ships
to other Ollama instances without assuming `websearch` or the `opencode-search`
plugin is configured. It lives at `config/opencode*/lov-sparql.ts` and is
copied into `~/.config/opencode/tools/` at boot (same pattern as `webfetch.ts`).

Knobs (env, all optional):

- `LOV_SPARQL_ENDPOINT` - override the endpoint URL (default `https://lov.linkeddata.es/dataset/sparql`)
- `LOV_SPARQL_TIMEOUT` - query timeout in seconds (default `30`, max `120`)

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