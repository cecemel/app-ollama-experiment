#!/bin/sh
set -e

# Assemble the live opencode config: the fixed base (opencode.base.json) plus the
# swappable cloud model list from OLLAMA_CLOUD_MODELS. opencode reads the result
# from ~/.config/opencode/opencode.json. A bad OLLAMA_CLOUD_MODELS warns and is
# skipped - it never crashes the container.
mkdir -p /root/.config/opencode
node -e '
const fs = require("fs");
const cfg = JSON.parse(fs.readFileSync("/etc/opencode/opencode.base.json", "utf8"));
const raw = (process.env.OLLAMA_CLOUD_MODELS || "").trim();
if (raw) {
  try {
    cfg.provider["ollama-cloud"].models = JSON.parse(raw);
  } catch (e) {
    console.error("WARNING: OLLAMA_CLOUD_MODELS is not valid JSON - skipping cloud models.");
    console.error("  expected a JSON object, e.g. { \"qwen3-coder:480b\": { \"tools\": true } }");
    console.error("  got: " + e.message);
  }
}
fs.writeFileSync("/root/.config/opencode/opencode.json", JSON.stringify(cfg, null, 2));
console.log("opencode config ready; cloud models: " + (Object.keys(cfg.provider["ollama-cloud"].models).join(", ") || "(none)"));
'

# Stay alive; exec in to use opencode.
exec sleep infinity
