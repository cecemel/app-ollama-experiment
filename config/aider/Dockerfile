FROM paulgauthier/aider-full:v0.86.2

USER root

# 1. Install extra dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup the working directory
WORKDIR /workspace

# 3. Copy start script
COPY start.sh /root/config/start.sh
RUN chmod +x /root/config/start.sh

ENTRYPOINT ["/bin/bash", "/root/config/start.sh"]