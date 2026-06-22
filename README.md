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

### Extra nodes
#### Running locally
To allow opencode top be agentic, the model must support tool-calling.
Check for the `tools` tag on the model's page on the [Ollama library](https://ollama.ai/library).
Also: `OLLAMA_CONTEXT_LENGTH: "32768"`, else it will choke.
#### Running with Ollama-cloud
```
  services:
    opencode:
      environment:
        OLLAMA_API_KEY: "<insert your API key here>"
        OPENCODE_CONFIG_CONTENT: |
          {
            "model": "ollama-cloud/qwen3-coder:480b",
            "small_model": "ollama-cloud/gpt-oss:20b",
            "provider": {
              "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "options": { "baseURL": "http://ollama:11434/v1" },
                "models": { "llama3.2:3b": { "tools": true } }
              },
              "ollama-cloud": {
                "npm": "@ai-sdk/openai-compatible",
                "options": { "baseURL": "https://ollama.com/v1", "apiKey": "{env:OLLAMA_API_KEY}" },
                "models": {
                  "qwen3-coder:480b": { "tools": true },
                  "gpt-oss:120b": { "tools": true },
                  "glm-5.2:cloud": { "tools": true }
                }
              }
            }
          }
```


####

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

## Sample docker-compose.override.yml configs
```
services:
  ollama:
    environment:
      MODEL: "qwen3:8b"

  opencode:
    environment:
      OPENCODE_CONFIG_CONTENT: |
        {
          "model": "ollama/qwen3:8b",
          "small_model": "ollama/qwen3:8b",
          "provider": {
            "ollama": {
              "npm": "@ai-sdk/openai-compatible",
              "options": { "baseURL": "http://ollama:11434/v1" },
              "models": { "qwen3:8b": { "tools": true } }
            }
          }
        }
    volumes:
    - /path/to/your/repo:/workspace/repo

  aider:
    environment:
      AIDER_MODEL: "ollama/qwen3:8b"
```
