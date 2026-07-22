# HuggingFace local runtime - llama.cpp (PrismML fork).
#
# Runs the Ternary-Bonsai / Bonsai 2-bit ("Q2_0_g128") GGUF models from HF. These
# GGUFs need PrismML's fork of llama.cpp - mainline llama.cpp cannot load the
# group-128 Q2_0 files (see https://github.com/PrismML-Eng/llama.cpp).
#
# The image pulls a prebuilt llama-server binary from the fork's GitHub release
# (no source build), then runs start.sh which downloads the model from HF on
# first boot and serves an OpenAI-compatible /v1 endpoint on port 8080. opencode
# picks it up via the "huggingface-local" provider (opencode.base.json).
#
# Pick a backend at build time:
#   --build-arg BACKEND=cpu        Linux x86-64, CPU only (default; smallest, no GPU deps)
#   --build-arg BACKEND=cuda-12.8  Linux x86-64 + CUDA 12.8
#   --build-arg BACKEND=cuda-12.4  Linux x86-64 + CUDA 12.4
#   --build-arg BACKEND=vulkan     Linux x86-64, Vulkan (AMD iGPU/Phoenix3, Intel Arc)
#   --build-arg BACKEND=rocm-7.2   Linux x86-64, ROCm 7.2 (AMD - discrete/datacenter only)
# The CUDA build needs the host to have matching NVIDIA drivers; ROCm needs the
# ROCm runtime on the host. Vulkan is self-contained: the Mesa RADV driver ships
# with the image, so any host with a Vulkan-capable GPU + /dev/dri works.
# All GPU backends need /dev/dri (or nvidia*) device passthrough at runtime -
# see docker-compose.override.yml for the device_cgroup rule.

ARG BACKEND=cpu
ARG RELEASE_TAG=prism-b9596-9fcaed7

FROM ubuntu:24.04 AS base
ARG RELEASE_TAG
ARG BACKEND
# Vulkan needs the loader + Mesa's RADV userspace driver to talk to the AMD iGPU.
# The prebuilt binary links against libvulkan; CPU builds only need libgomp1.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl tar libgomp1 \
      $(case "$BACKEND" in vulkan) echo "libvulkan1 mesa-vulkan-drivers vulkan-tools";; esac) \
    && rm -rf /var/lib/apt/lists/*

# Map backend -> release-asset name. PrismML publishes these as .tar.gz archives
# with a `build/bin/llama-server` inside.
RUN case "$BACKEND" in \
      cpu)       ASSET="llama-${RELEASE_TAG}-bin-ubuntu-x64.tar.gz" ;; \
      cuda-12.8) ASSET="llama-${RELEASE_TAG}-bin-linux-cuda-12.8-x64.tar.gz" ;; \
      cuda-12.4) ASSET="llama-${RELEASE_TAG}-bin-linux-cuda-12.4-x64.tar.gz" ;; \
      vulkan)    ASSET="llama-${RELEASE_TAG}-bin-ubuntu-vulkan-x64.tar.gz" ;; \
      rocm-7.2)  ASSET="llama-${RELEASE_TAG}-bin-ubuntu-rocm-7.2-x64.tar.gz" ;; \
      *) echo "Unknown BACKEND=$BACKEND" && exit 2 ;; \
    esac && \
    echo "Fetching llama.cpp (PrismML fork) binary: $ASSET" && \
    curl -fsSL -o /tmp/llama.tar.gz \
      "https://github.com/PrismML-Eng/llama.cpp/releases/download/${RELEASE_TAG}/${ASSET}" && \
    mkdir -p /opt/llama && tar -xzf /tmp/llama.tar.gz -C /opt/llama && \
    rm /tmp/llama.tar.gz && \
    BIN=$(find /opt/llama -type f -name llama-server -print -quit) && \
    test -n "$BIN" && ln -sf "$BIN" /usr/local/bin/llama-server

# HF_HOME so downloaded GGUFs cache under /data (mounted to ./data/huggingface-local)
# and survive container rebuilds.
ENV HF_HOME=/data \
    HUGGINGFACE_HUB_CACHE=/data/hub \
    LLAMA_ARG_HOST=0.0.0.0 \
    LLAMA_ARG_PORT=8080

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/start.sh"]
