# app-ollama-experiment

Local AI experiment running several agents on top of a local [Ollama](https://ollama.ai/) model:

- **Coding agent** (`opencode`) - edits code in your local repos via [opencode](https://opencode.ai/)
- **Coding agent** (`opencode-light`) - stripped-down opencode for small/local models: no LSP, formatter, MCP, plugins, instructions, skills or subagents, so nothing fills the context that a small model can't use. Only `read` + `edit` + `bash` + `glob` + `grep` tools are exposed.
- **Connected agent** (`agent`) - chat with a model that can reach out to the web when it needs to

By default runs `llama3.2:3b` (~2GB) - small and tool-calling capable, so every agent below works
out of the box.

## Getting started

```
drc up -d
```

It might take a while to fetch the model the first time. Check the ollama logs to follow progress:

```
drc logs -f ollama
```

To mount your own repos into a coding agent, create a `docker-compose.override.yml` (gitignored by
convention, so it stays local):

```yaml
services:
  opencode:
    volumes:
      - /path/to/your/repo:/workspace/repo
```

Then `drc up -d` to apply.

## Coding agent (opencode)

```
drc exec opencode opencode
```

Fixed config - providers, LSP (TypeScript/JS + Python), default model - is baked into the image at
`config/opencode/opencode.base.json`. Two knobs in `docker-compose.yml`:

- `OLLAMA_API_KEY` - Ollama Cloud key (put it in a `.env`); empty = local-only.
- `OLLAMA_CLOUD_MODELS` - cloud models to register; edit the list to swap.

Default is local `llama3.2:3b`. Switch per run:

```
drc exec opencode opencode run --model ollama/llama3.2:3b           "..."   # local
drc exec opencode opencode run --model ollama-cloud/qwen3-coder:480b "..."  # cloud
```

Local needs a tool-calling model (`tools` tag on the [Ollama library](https://ollama.ai/library)); the
`ollama` service sets `OLLAMA_CONTEXT_LENGTH=32768` or tool-calls choke. List cloud ids:
`curl https://ollama.com/v1/models -H "Authorization: Bearer $OLLAMA_API_KEY"`.

## Coding agent (opencode-light)

Same idea as `opencode`, but trimmed for small/local models that choke on a large system prompt.
The image bakes in a stripped `config/opencode-light/opencode.base.json` and sets env vars
(`OPENCODE_DISABLE_CLAUDE_CODE`, `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT`,
`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`, `OPENCODE_DISABLE_PROJECT_CONFIG`) that drop Claude Code
fallback rules, skills, and any project-level `AGENTS.md` / `CONTEXT.md` / `CLAUDE.md` from the
system prompt. LSP, formatter, MCP, plugins, instructions, subagents and per-model-family system
prompts are all off; only `read`, `edit`, `bash`, `glob` and `grep` tools are exposed (see the
`permission` block in the base config). It uses a separate data dir
(`./data/opencode-light/`) so it doesn't collide with the full `opencode` service.

```
drc exec opencode-light opencode
```

Same model env knobs as `opencode` (`OLLAMA_API_KEY`, `OLLAMA_LOCAL_MODELS`,
`OLLAMA_CLOUD_MODELS`, `OPENCODE_MODEL`, `OPENCODE_SMALL_MODEL`) and the same chat-logging proxy
(`OPENCODE_LOG_CHAT`, `CHAT_LOG_MAXLEN`). The custom Firefox-UA `webfetch` tool is copied in at
boot but denied by default - flip `webfetch` to `allow` in the permission block to use it.
Language servers (TypeScript/JS + Python via pyright) are baked into the image so you can re-enable
LSP per-project without rebuilding.

## Connected agent

An interactive CLI to chat with the model. When it needs to, it'll reach out - search DuckDuckGo, read a URL, or call an API. You can ask it anything; it figures out whether it needs the internet or not.

```
drc exec agent run
```

Type `exit` or `quit` to stop.

## Accessing the raw model

To chat with the model directly via the Ollama CLI (no tools, no agent wrapper):

```
drc exec ollama ollama run llama3.2:3b
```

Type `/bye` to exit.

## Choosing a model

Overview of available models: https://ollama.ai/library

Update the `MODEL` environment variable in `docker-compose.yml`:

```yaml
    environment:
      MODEL: "mistral"
```
