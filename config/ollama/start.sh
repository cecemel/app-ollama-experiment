#!/bin/bash

# 1. Start the Ollama server in the background
# We bind it to 0.0.0.0 so it's accessible outside the container
export OLLAMA_HOST=0.0.0.0
/bin/ollama serve &
OLLAMA_PID=$!

# 2. Wait for the API to be active (Universal check)
# Instead of a fixed 'sleep 30s', this loop checks the actual service status
echo "Waiting for Ollama server to respond..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 2
done
echo "Ollama server ready..."

# 3. Pull the requested model
# This works for any model name passed in the $MODEL variable
if [ -n "$MODEL" ]; then
  echo "Ensuring model '$MODEL' is downloaded..."
  /bin/ollama pull "$MODEL"

  # 4. Optional: Pre-load the model into memory
  # This makes the first request fast regardless of model size
  echo "Warming up '$MODEL'..."
  curl -s -X POST http://localhost:11434/api/generate -d "{\"model\": \"$MODEL\"}" > /dev/null
else
  echo "No MODEL variable detected. Server is running, but no model pre-loaded."
fi

echo "------------------------------------------------------------"
echo "Ollama is up and running with model: ${MODEL:-none}"
echo "External API Port: 11434"
echo "------------------------------------------------------------"

# 5. The "Keep-Alive" Monitor
# This keeps the container running as long as the 'serve' process exists
while ps -p $OLLAMA_PID > /dev/null; do
    sleep 60
done

echo "Ollama process lost. Exiting container."
exit 1
