# app-ollama-experiment

Local AI experiment running two agents on top of a local [Ollama](https://ollama.ai/) model:

- **Coding agent** (`aider`) — edits code in your local repos via [Aider](https://aider.chat/)
- **Research agent** (`agent`) — answers questions using web search (DuckDuckGo), URL scraping, and JSON API calls

By default runs `gemma4:e4b` (~9GB).

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

## Research agent

The research agent is an interactive CLI that can search the web via DuckDuckGo, scrape URLs, and call JSON APIs to answer your questions. The model decides which tools to use based on your question.

Start a session:

```
drc exec agent run
```

You'll see real-time output as the agent works — which tools it's calling, raw results, and when it's summarizing. Type `exit` or `quit` to stop.

## Accessing the raw model

To chat with the model directly via the Ollama CLI (no tools, no agent wrapper):

```
drc exec ollama ollama run gemma4:e4b
```

Type `/bye` to exit.

## Choosing a model

Overview of available models: https://ollama.ai/library

Update the `MODEL` environment variable in `docker-compose.yml`:

```yaml
    environment:
      MODEL: "mistral"
```

For the coding agent, also update `AIDER_MODEL` to match:

```yaml
    environment:
      AIDER_MODEL: "ollama/mistral"
```

Then `drc up -d` to apply.
