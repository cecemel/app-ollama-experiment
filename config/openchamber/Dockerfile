FROM node:24-slim

# git for terminal/repo features (optional); ca-certificates so openchamber's
# own outbound HTTPS (update checks, relay dial) verifies.
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# OpenChamber web app (CLI). Connects to the external opencode server via
# OPENCODE_HOST + OPENCODE_SKIP_START=true (set in docker-compose.yml), so it
# does not run its own opencode. Pin the version, same as the opencode image.
RUN npm install -g @openchamber/web@2.4.0

# Bind the web UI on all interfaces so it's reachable from the host / LAN.
# Override OPENCHAMBER_UI_PASSWORD in docker-compose.override.yml.
ENV OPENCHAMBER_HOST=0.0.0.0

EXPOSE 3000

WORKDIR /workspace

CMD ["openchamber"]