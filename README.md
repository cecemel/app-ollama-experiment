# app-ollama-experiment

Local AI coding assistant using [Ollama](https://ollama.ai/) + [Aider](https://aider.chat/).

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
