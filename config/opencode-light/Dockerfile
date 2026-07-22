FROM node:22-slim

# git for repo work; python3 so the Python LSP (pyright) can resolve an interpreter.
# LSP/formatter are OFF by default in opencode-light (see opencode.base.json), but
# pyright + typescript-language-server are still baked in so you can flip them on
# per-project without rebuilding.
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y xclip wl-clipboard && rm -rf /var/lib/apt/lists/*

# opencode CLI + language servers for JS/TS and Python. LSP is off by default and
# these are not auto-installed, so bake them in. (opencode pinned - see https://opencode.ai)
RUN npm install -g \
      opencode-ai@1.18.1 \
      typescript \
      typescript-language-server \
      pyright

# Make the global typescript resolvable from any project (for the TS language server)
ENV NODE_PATH=/usr/local/lib/node_modules

# Fixed config (providers + stripped prompts) is baked in; start.sh assembles the
# live config at boot, splicing in the swappable OLLAMA_CLOUD_MODELS env var.
# start.sh also exports the env vars that disable Claude Code compatibility files
# (CLAUDE.md / ~/.claude/skills) so none of that extra context is ever injected.
COPY opencode.base.json /etc/opencode/opencode.base.json
COPY start.sh /etc/opencode/start.sh
COPY proxy.js /etc/opencode/proxy.js
COPY webfetch.ts /etc/opencode/webfetch.ts

WORKDIR /workspace

# These are static for the light image - they strip Claude Code fallback rules,
# skills and any project-level AGENTS.md / CONTEXT.md from the system prompt
ENV OPENCODE_DISABLE_CLAUDE_CODE=1 \
    OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1 \
    OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1 \
    OPENCODE_DISABLE_PROJECT_CONFIG=1

CMD ["sh", "/etc/opencode/start.sh"]
