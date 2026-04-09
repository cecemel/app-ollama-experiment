FROM paulgauthier/aider-full:v0.86.2

USER root

# 1. Install GitHub CLI
RUN apt-get update && apt-get install -y --no-install-recommends curl gpg \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
       | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
       > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup the working directory
WORKDIR /workspace

# 3. Create directories writable by appuser
RUN mkdir -p /workspace/.aider \
    && chown -R appuser:appuser /workspace/.aider

# 4. Copy start script
COPY start.sh /root/config/start.sh
RUN chmod +x /root/config/start.sh

ENTRYPOINT ["/bin/bash", "/root/config/start.sh"]