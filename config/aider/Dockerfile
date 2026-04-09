FROM paulgauthier/aider-full:v0.86.2

USER root

# 1. Install GitHub CLI
RUN apt-get update && apt-get install -y --no-install-recommends curl

# 2. Setup the working directory
WORKDIR /workspace

# 3. Create directories writable by appuser
RUN mkdir -p /workspace/.aider \
    && chown -R appuser:appuser /workspace/.aider

# 4. Copy start script
COPY start.sh /root/config/start.sh
RUN chmod +x /root/config/start.sh

ENTRYPOINT ["/bin/bash", "/root/config/start.sh"]