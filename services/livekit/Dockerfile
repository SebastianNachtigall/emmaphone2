FROM livekit/livekit-server:latest

# Install Python for our debug server (Alpine uses apk, not apt-get)
RUN apk add --no-cache python3

# Expose the necessary ports
EXPOSE 7880

# Copy our debug server
COPY test-server-with-livekit.py /test-server.py
RUN chmod +x /test-server.py

# Start our debug server that will also test LiveKit
CMD ["python3", "/test-server.py"]