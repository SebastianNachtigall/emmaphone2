# Try a different approach - use Alpine and install LiveKit manually
FROM alpine:latest

# Install required packages
RUN apk add --no-cache \
    bash \
    curl \
    wget \
    ca-certificates \
    openssl

# Download and install LiveKit server
RUN wget -O /tmp/livekit-server.tar.gz https://github.com/livekit/livekit/releases/download/v1.4.3/livekit_1.4.3_linux_amd64.tar.gz && \
    tar -xzf /tmp/livekit-server.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/livekit-server && \
    rm /tmp/livekit-server.tar.gz

# Copy our config and scripts
COPY livekit.yaml /etc/livekit.yaml
COPY start-livekit.sh /start-livekit.sh
RUN chmod +x /start-livekit.sh

# Expose the default LiveKit ports
EXPOSE 7880 7881

# Use our startup script
CMD ["/start-livekit.sh"]