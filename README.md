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


Once inside, navigate to your project and start aider:

```
```

Then `drc up -d` to apply. The override file is gitignored by convention, so it stays local.

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

