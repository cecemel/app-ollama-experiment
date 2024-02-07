#!/bin/bash
/bin/ollama serve &
echo "Sleeping 30 seconds before loading model..."
sleep 30s
echo "Loading model: $MODEL"
echo "If this is the first time you are loading this model; this might take while to boot."
/bin/ollama run $MODEL
echo "Model $MODEL should be running. It's accessible through the API or in the container with command: "
echo "drc exec ollama ollama run $MODEL";
while true; do sleep 10h; done
