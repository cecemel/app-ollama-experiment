# app-ollama-experiment

Local AI coding assistant using [Ollama](https://ollama.ai/) + [Aider](https://aider.chat/).

By default runs `gemma4:e4b` (~9GB).

## Getting started

```
drc up -d
```

It might take a while to fetch the model the first time. Check the ollama logs to follow progress:

```
drc logs -f ollama
```

## Using aider

The aider container stays alive in the background. Exec into it to start an interactive session:

```
drc exec aider bash
```

Once inside, navigate to your project and start aider:

```
cd /workspace/my-project
aider
```

## Mounting your project

Create a `docker-compose.override.yml` to mount the repo(s) you want aider to work on:

```yaml
services:
  aider:
    volumes:
      - /path/to/your/repo:/workspace/repo
```

Then `drc up -d` to apply. The override file is gitignored by convention, so it stays local.

## Agent — web research CLI

The `agent` service is an interactive CLI agent that can search the web, scrape URLs, and call JSON APIs to answer your questions.

Start an agent session:

```
drc exec agent run
```

You'll be prompted to type a question. The agent will decide which tools to use, execute them, and summarize the results. You can see what it's doing in real time — tool calls, raw output, and model status are all printed as it works.

Type `exit` or `quit` to stop.

### Accessing the raw model directly

To chat with the model directly via the Ollama CLI (no tools, no agent wrapper):

```
drc exec ollama ollama run gemma4:e4b
```

Or drop into a shell first:

```
drc exec ollama bash
ollama run gemma4:e4b
```

Type `/bye` to exit the Ollama session.

## Choosing a model

Overview of available models: https://ollama.ai/library

Update the `MODEL` environment variable in `docker-compose.yml`:

```yaml
    environment:
      MODEL: "mistral"
```

Make sure to also update `AIDER_MODEL` on the aider service to match:

```yaml
    environment:
      AIDER_MODEL: "ollama/mistral"
```

Then `drc up -d` to apply.
