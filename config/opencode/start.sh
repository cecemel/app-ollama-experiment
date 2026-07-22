#!/bin/sh
set -e

# Assemble the live opencode config: the fixed base (opencode.base.json) plus the
# swappable model lists - OLLAMA_LOCAL_MODELS, OLLAMA_CLOUD_MODELS, WEAVE_MODELS
# and PRISM_MODELS. opencode reads the result from ~/.config/opencode/opencode.json.
# A bad list warns and is skipped - it never crashes the container.
mkdir -p /root/.config/opencode
# Custom webfetch tool (normal Firefox User-Agent). The tools dir is on the mounted
# config volume, so we drop it in at boot rather than baking it into the image path.
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
apply("OLLAMA_LOCAL_MODELS", "ollama-local");
apply("OLLAMA_CLOUD_MODELS", "ollama-cloud");
apply("WEAVE_MODELS", "weave");
apply("PRISM_MODELS", "llama-prism");
if (process.env.OPENCODE_MODEL) cfg.model = process.env.OPENCODE_MODEL.trim();
if (process.env.OPENCODE_SMALL_MODEL) cfg.small_model = process.env.OPENCODE_SMALL_MODEL.trim();
// When chat logging is on, route the providers through the local logging proxy.
if (process.env.OPENCODE_LOG_CHAT === "true") {
  const port = process.env.CHAT_LOG_PORT || "8787";
  cfg.provider["ollama-local"].options.baseURL = "http://localhost:" + port + "/local/v1";
  cfg.provider["ollama-cloud"].options.baseURL = "http://localhost:" + port + "/cloud/v1";
  cfg.provider.weave.options.baseURL = "http://localhost:" + port + "/weave/v1";
  cfg.provider["llama-prism"].options.baseURL = "http://localhost:" + port + "/prism/v1";
}
fs.writeFileSync("/root/.config/opencode/opencode.json", JSON.stringify(cfg, null, 2));
const k = p => Object.keys(cfg.provider[p].models).join(", ") || "(none)";
console.log("opencode config ready; model: " + cfg.model + " | local: " + k("ollama-local") + " | cloud: " + k("ollama-cloud") + " | weave: " + k("weave") + " | prism: " + k("llama-prism") + (process.env.OPENCODE_LOG_CHAT === "true" ? " | chat-logging: ON" : ""));
'

# With chat logging on, the proxy is the main process (logs traffic to docker logs and
# keeps the container alive). Otherwise just idle.
if [ "$OPENCODE_LOG_CHAT" = "true" ]; then
  exec node /etc/opencode/proxy.js
else
  exec sleep infinity
fi
