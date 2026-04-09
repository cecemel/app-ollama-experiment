FROM ollama/ollama:0.20.3

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Create the config directory
RUN mkdir -p /root/config

# Copy the local start.sh script into the image
# Make sure start.sh is in the same folder as this Dockerfile
COPY start.sh /root/config/start.sh

# Give execution permissions to the script
RUN chmod +x /root/config/start.sh

# Expose the default Ollama port
EXPOSE 11434

# Set the entrypoint
ENTRYPOINT ["/bin/bash", "/root/config/start.sh"]