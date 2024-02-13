# app-ollama-experiment
## running
```
drc up -d
```
It might take a while to fetch the model the first time.
The easiest will be to connect in the container, a CLI will be at your disposal.
Check the logs, the command to run the CLI wil be displayed once `ollama` is properly started.

The api should boot too, but this *may* vary per model.(to check) You'll have to portmap the container.
```
  ports:
   - 80:11434
```
### running another  a model
Overview of the modes: https://ollama.ai/library
Then it's a matter of updating the environment variable.
```
    environment:
      MODEL: "mistral" # as an example.
```
and `drc up -d`
