FROM node:22-slim

# Tools the coding agent needs to work on real repos
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the opencode CLI (pinned for reproducibility - see https://opencode.ai)
RUN npm install -g opencode-ai@1.17.9

WORKDIR /workspace

# The container just stays alive; exec in to use it. opencode reads its entire
# config from the OPENCODE_CONFIG_CONTENT env var (set in docker-compose.yml).
CMD ["sleep", "infinity"]
