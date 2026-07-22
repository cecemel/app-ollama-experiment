#!/bin/sh
set -e

# Assemble the live opencode config: the fixed base (opencode.base.json) plus the
# swappable model lists - OLLAMA_LOCAL_MODELS, OLLAMA_CLOUD_MODELS, WEAVE_MODELS
# and HF_MODELS. opencode reads the result from ~/.config/opencode/opencode.json.
# A bad list warns and is skipped - it never crashes the container.
mkdir -p /root/.config/opencode
# Custom webfetch tool (normal Firefox User-Agent). The tools dir is on the mounted
# config volume, so we drop it in at boot rather than baking it into the image path.
# webfetch/websearch are allowed by default (same as the full opencode config);
# set OPENCODE_LIGHT_WEBFETCH=deny in docker-compose.yml to turn them off.
mkdir -p /root/.config/opencode/tools
cp /etc/opencode/webfetch.ts /root/.config/opencode/tools/webfetch.ts
node -e '
const fs = require("fs");
const cfg = JSON.parse(fs.readFileSync("/etc/opencode/opencode.base.json", "utf8"));
function apply(envName, providerId) {
  const raw = (process.env[envName] || "").trim();
  if (!raw) return;
  try {
    cfg.provider[providerId].models = JSON.parse(raw);
  } catch (e) {
    console.error("WARNING: " + envName + " is not valid JSON - skipping " + providerId + " models.");
    console.error("  expected a JSON object, e.g. { \"llama3.2:3b\": { \"tools\": true } }");
    console.error("  got: " + e.message);
  }
}
apply("OLLAMA_LOCAL_MODELS", "ollama");
apply("OLLAMA_CLOUD_MODELS", "ollama-cloud");
apply("WEAVE_MODELS", "weave");
apply("HF_MODELS", "huggingface-local");
if (process.env.OPENCODE_MODEL) cfg.model = process.env.OPENCODE_MODEL.trim();
if (process.env.OPENCODE_SMALL_MODEL) cfg.small_model = process.env.OPENCODE_SMALL_MODEL.trim();
// webfetch/websearch are allowed by default (same as the full opencode config) -
// the custom Firefox-UA webfetch tool is copied in below. Set
// OPENCODE_LIGHT_WEBFETCH=deny to turn it off if you want the extra-tight context.
if (process.env.OPENCODE_LIGHT_WEBFETCH === "deny") {
  cfg.permission.webfetch = "deny";
  cfg.permission.websearch = "deny";
}
// When chat logging is on, route the providers through the local logging proxy.
if (process.env.OPENCODE_LOG_CHAT === "true") {
  const port = process.env.CHAT_LOG_PORT || "8787";
  cfg.provider.ollama.options.baseURL = "http://localhost:" + port + "/local/v1";
  cfg.provider["ollama-cloud"].options.baseURL = "http://localhost:" + port + "/cloud/v1";
  cfg.provider.weave.options.baseURL = "http://localhost:" + port + "/weave/v1";
  cfg.provider["huggingface-local"].options.baseURL = "http://localhost:" + port + "/hf/v1";
}
fs.writeFileSync("/root/.config/opencode/opencode.json", JSON.stringify(cfg, null, 2));
const k = p => Object.keys(cfg.provider[p].models).join(", ") || "(none)";
console.log("opencode-light config ready; model: " + cfg.model + " | local: " + k("ollama") + " | cloud: " + k("ollama-cloud") + " | weave: " + k("weave") + " | hf: " + k("huggingface-local") + " | webfetch: " + (cfg.permission.webfetch || "allow") + (process.env.OPENCODE_LOG_CHAT === "true" ? " | chat-logging: ON" : ""));
'

# Belt-and-braces: the Dockerfile already sets these, but export them again in case
# docker-compose.yml overrides ENV. These strip Claude Code fallback instructions,
# skills, and any project-level AGENTS.md / CONTEXT.md / CLAUDE.md so nothing extra
# is injected into the system prompt for small models.
export OPENCODE_DISABLE_CLAUDE_CODE=1
export OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1
export OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1
export OPENCODE_DISABLE_PROJECT_CONFIG=1

# With chat logging on, the proxy is the main process (logs traffic to docker logs and
# keeps the container alive). Otherwise just idle.
if [ "$OPENCODE_LOG_CHAT" = "true" ]; then
  exec node /etc/opencode/proxy.js
else
  exec sleep infinity
fi
