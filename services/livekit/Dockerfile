FROM livekit/livekit-server:latest

# Install Python for our debug server
RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*

# Expose the necessary ports
EXPOSE 7880

# Copy our debug server
COPY test-server-with-livekit.py /test-server.py
RUN chmod +x /test-server.py

# Start our debug server that will also test LiveKit
CMD ["python3", "/test-server.py"]