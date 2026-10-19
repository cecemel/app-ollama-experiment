# Thin wrapper around the upstream self-hosted OpenChamber relay, reconfigured to
# listen on port 80 so an external TLS terminator (Let's Encrypt / reverse proxy)
# can forward plain HTTP/WS to it. The relay is a stateless E2EE broker: it
# forwards already-encrypted frames between your openchamber instance and your
# paired devices, stores no secrets, and needs none.
#
# Upstream: https://github.com/openchamber/openchamber-relay
FROM ghcr.io/openchamber/openchamber-relay:latest

# Listen on :80 inside the container. The port mapping + TLS termination are
# handled outside this image (see docker-compose.yml / README).
ENV PORT=80

EXPOSE 80