#!/bin/bash
set -e

# llama.cpp (PrismML fork) launcher. Runs `llama-server -hf <repo>:<quant>` which
# downloads the GGUF from Hugging Face on first boot (cached under /data so it
# survives rebuilds) and serves an OpenAI-compatible /v1 endpoint on :8080.
#
# Knobs (env, override in docker-compose.yml / override file):
#   PRISM_MODEL       <user>/<model>[:quant]   default: prism-ml/Bonsai-27B-gguf:Q1_0  (1-bit, ~3.8GB)
#                                                alt: prism-ml/Ternary-Bonsai-27B-gguf:Q2_0 (ternary, ~7GB)
#   PRISM_TOKEN       HF access token          needed only while a repo is gated (the Bonsai repos are public)
#   PRISM_FILE        explicit file            overrides :quant in PRISM_MODEL
#   LLAMA_NGL         GPU layers to offload    99 = all (default); 0 = CPU only (ignored on cpu build)
#   LLAMA_CONTEXT     context window          32768 (tool-calling wants >= 16k)
#   LLAMA_ALIAS       model id reported to /v1 default: bonsai-27b-1bit (so opencode
#                                                calls it llama-prism/bonsai-27b-1bit)
#   LLAMA_EXTRA       extra flags              verbatim, shell-split
#   LLAMA_JINJA       use the GGUF's built-in chat template  default: 1 (needed for tool-calling;
#                                                the Qwen3.6 base template formats tool_calls)

PRISM_MODEL="${PRISM_MODEL:-prism-ml/Bonsai-27B-gguf:Q1_0}"
LLAMA_NGL="${LLAMA_NGL:-99}"
LLAMA_CONTEXT="${LLAMA_CONTEXT:-32768}"
LLAMA_ALIAS="${LLAMA_ALIAS:-bonsai-27b-1bit}"
LLAMA_JINJA="${LLAMA_JINJA:-1}"

# Split PRISM_MODEL into <repo>[:<quant>]. PRISM_FILE (if set) overrides the quant-based
# filename resolution, so it wins for the cache check.
REPO="${PRISM_MODEL%%:*}"
QUANT="${PRISM_MODEL#*:}"
[ "$QUANT" = "$REPO" ] && QUANT=""

# HF cache layout: $HUGGINGFACE_HUB_CACHE/models--<user>--<model>/snapshots/<commit>/<file>
# (HF_HOME / HUGGINGFACE_HUB_CACHE are set by the Dockerfile; default here in case
# start.sh runs outside the image. They're standard HuggingFace library env vars, kept
# as-is so llama-server's downloader caches under /data.)
HF_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-/data/hub}"
CACHE_DIR="$HF_HUB_CACHE/models--${REPO//\//--}"

# Figure out which file we expect, so we can tell "downloading" from "cached" before
# handing off to llama-server (whose own progress bar is easy to miss in docker logs).
shopt -s nullglob
if [ -n "$PRISM_FILE" ]; then
  MATCHES=("$CACHE_DIR"/snapshots/*/"$PRISM_FILE")
elif [ -n "$QUANT" ]; then
  MATCHES=("$CACHE_DIR"/snapshots/*/*"$QUANT"*.gguf)
else
  MATCHES=("$CACHE_DIR"/snapshots/*/*.gguf)
fi
shopt -u nullglob

if [ ${#MATCHES[@]} -gt 0 ]; then
  CACHED_FILE="${MATCHES[0]}"
  HUMAN_SIZE=$(du -h "$CACHED_FILE" 2>/dev/null | cut -f1 || echo "?")
  echo "Model '$LLAMA_ALIAS' ($PRISM_MODEL) found in HF cache ($HUMAN_SIZE) - no download needed."
else
  # Also surface an interrupted/resuming download if huggingface_hub left a .incomplete
  INCOMPLETE=$(find "$CACHE_DIR" -name '*.incomplete' 2>/dev/null | head -1)
  echo "================================================================"
  if [ -n "$INCOMPLETE" ]; then
    echo "Model '$LLAMA_ALIAS' ($PRISM_MODEL) is resuming download from Hugging Face..."
  else
    echo "Model '$LLAMA_ALIAS' ($PRISM_MODEL) is downloading from Hugging Face..."
  fi
  echo "This happens on first boot only; it's cached under $HF_HUB_CACHE for next time."
  echo "Follow the progress bar below."
  echo "================================================================"
fi

# --hf-repo/--hf-token/--hf-file are llama-server's own CLI flags (the binary downloads
# from Hugging Face); they stay named --hf-* regardless of the PRISM_* env that feeds them.
ARGS=(--hf-repo "$PRISM_MODEL" --host 0.0.0.0 --port 8080 -ngl "$LLAMA_NGL" -c "$LLAMA_CONTEXT" --alias "$LLAMA_ALIAS")
# --jinja makes llama-server use the chat template baked into the GGUF metadata
# instead of the llama.cpp default. The Bonsai GGUF ships the Qwen3.6 template,
# which knows how to format tool_calls - without --jinja, tool-calling doesn't work.
[ "$LLAMA_JINJA" = "1" ] && ARGS+=(--jinja)
[ -n "$PRISM_TOKEN" ] && ARGS+=(--hf-token "$PRISM_TOKEN")
[ -n "$PRISM_FILE"  ] && ARGS+=(--hf-file "$PRISM_FILE")
[ -n "$LLAMA_EXTRA" ] && { # shellcheck disable=SC2086
  ARGS+=($LLAMA_EXTRA)
}

echo "Starting llama-server: ${ARGS[*]}"
exec llama-server "${ARGS[@]}"
