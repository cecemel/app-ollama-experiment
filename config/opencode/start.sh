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
# LOV SPARQL tool: searches the Linked Open Vocabularies registry for RDF
# vocabularies. Self-contained (uses only global fetch); does not need
# websearch or the opencode-search plugin to be configured.
cp /etc/opencode/lov-sparql.ts /root/.config/opencode/tools/lov-sparql.ts
# Personal global rules: opencode auto-discovers ~/.config/opencode/AGENTS.md and
# applies it to every session. The source is bind-mounted (gitignored) from
# docker-compose.override.yml; copy it in at boot so the rules load via the
# global mechanism rather than the instructions array (more robust across
# sessions, no path dependency). Warn if the source is missing or empty.
if [ -s /etc/opencode/AGENTS.md ]; then
  cp /etc/opencode/AGENTS.md /root/.config/opencode/AGENTS.md
else
  echo "WARNING: /etc/opencode/AGENTS.md is missing or empty - personal rules won't load."
fi
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
apply("LOCALHOST_GATEWAY_MODELS", "localhost-gateway");
if (process.env.OPENCODE_MODEL) cfg.model = process.env.OPENCODE_MODEL.trim();
if (process.env.OPENCODE_SMALL_MODEL) cfg.small_model = process.env.OPENCODE_SMALL_MODEL.trim();
// Keep the build agent default model in sync with OPENCODE_MODEL. The "max"
// variant is GLM-5.2-only; drop it when overridden to a different model (most
// providers do not have a "max" variant and would error).
if (cfg.agent && cfg.agent.build) {
  const m = process.env.OPENCODE_MODEL ? process.env.OPENCODE_MODEL.trim() : "ollama-cloud/glm-5.2";
  cfg.agent.build.model = m;
  cfg.agent.build.variant = /\/glm-5\.2($|@)/.test(m) ? "max" : undefined;
}
// When chat logging is on, route the providers through the local logging proxy.
if (process.env.OPENCODE_LOG_CHAT === "true") {
  const port = process.env.CHAT_LOG_PORT || "8787";
  cfg.provider["ollama-local"].options.baseURL = "http://localhost:" + port + "/local/v1";
  cfg.provider["ollama-cloud"].options.baseURL = "http://localhost:" + port + "/cloud/v1";
  cfg.provider.weave.options.baseURL = "http://localhost:" + port + "/weave/v1";
  cfg.provider["llama-prism"].options.baseURL = "http://localhost:" + port + "/prism/v1";
  cfg.provider["localhost-gateway"].options.baseURL = "http://localhost:" + port + "/gateway/v1";
}
fs.writeFileSync("/root/.config/opencode/opencode.json", JSON.stringify(cfg, null, 2));
const k = p => Object.keys(cfg.provider[p].models).join(", ") || "(none)";
console.log("opencode config ready; model: " + cfg.model + " | local: " + k("ollama-local") + " | cloud: " + k("ollama-cloud") + " | weave: " + k("weave") + " | prism: " + k("llama-prism") + " | gateway: " + k("localhost-gateway") + (process.env.OPENCODE_LOG_CHAT === "true" ? " | chat-logging: ON" : ""));
'

# With chat logging on, the proxy is the main process (logs traffic to docker logs and
# keeps the container alive). Otherwise just idle.
if [ "$OPENCODE_LOG_CHAT" = "true" ]; then
  exec node /etc/opencode/proxy.js
else
  exec sleep infinity
fi
