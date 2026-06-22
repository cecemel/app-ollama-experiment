FROM node:22-slim

# git for repo work; python3 so the Python LSP (pyright) can resolve an interpreter
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y xclip wl-clipboard && rm -rf /var/lib/apt/lists/*

# opencode CLI + language servers for JS/TS and Python. LSP is off by default and
# these are not auto-installed, so bake them in. (opencode pinned - see https://opencode.ai)
RUN npm install -g \
      opencode-ai@1.17.9 \
      typescript \
      typescript-language-server \
      pyright

# Make the global typescript resolvable from any project (for the TS language server)
ENV NODE_PATH=/usr/local/lib/node_modules

# Fixed config (providers + lsp) is baked in; start.sh assembles the live config at
# boot, splicing in the swappable OLLAMA_CLOUD_MODELS env var.
COPY opencode.base.json /etc/opencode/opencode.base.json
COPY start.sh /etc/opencode/start.sh
COPY proxy.js /etc/opencode/proxy.js

WORKDIR /workspace

CMD ["sh", "/etc/opencode/start.sh"]
