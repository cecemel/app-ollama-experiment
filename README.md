# app-ollama-experiment

Local AI experiment running several agents on top of a local [Ollama](https://ollama.ai/) model:

- **Coding agent** (`aider`) - edits code in your local repos via [Aider](https://aider.chat/)
- **Coding agent** (`opencode`) - edits code in your local repos via [opencode](https://opencode.ai/)
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

## Coding agent (aider)

The aider container stays alive in the background. Exec into it to start an interactive session:

```
drc exec aider bash
```

Once inside, navigate to your project and start aider:

```
cd /workspace/my-project
aider
```

### Mounting your project

Create a `docker-compose.override.yml` to mount the repo(s) you want aider to work on:

```yaml
services:
  aider:
    volumes:
      - /path/to/your/repo:/workspace/repo
```

Then `drc up -d` to apply. The override file is gitignored by convention, so it stays local.

## Coding agent (opencode)

Like aider, but [opencode](https://opencode.ai/). The container idles; exec in:

```
drc exec opencode opencode                         # interactive
drc exec opencode opencode run "explain this repo"  # one-shot
```

Configured by `OPENCODE_CONFIG_CONTENT` in `docker-compose.yml` (inline JSON, default `llama3.2:3b`).
Editing works out of the box. Model and repo-mount details: [`config/opencode/README.md`](./config/opencode/README.md).

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

For the aider coding agent, also update `AIDER_MODEL` to match:

```yaml
    environment:
      AIDER_MODEL: "ollama/mistral"
```
### Note about opencode
To allow opencode top be agentic, the model must support tool-calling.
Check for the `tools` tag on the model's page on the [Ollama library](https://ollama.ai/library).
Also: `OLLAMA_CONTEXT_LENGTH: "32768"`, else it will choke.
