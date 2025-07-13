FROM livekit/livekit-server:latest

# Copy configuration
COPY livekit-railway.yaml /etc/livekit.yaml

# Expose the necessary ports
EXPOSE 7880
EXPOSE 7881
EXPOSE 50000-60000/udp

# Start LiveKit server
CMD ["livekit-server", "--config", "/etc/livekit.yaml"]