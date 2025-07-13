FROM livekit/livekit-server:latest

# Install basic tools including netcat for simple web server
RUN apk add --no-cache bash netcat-openbsd python3

# Expose the necessary ports
EXPOSE 7880

# Copy our scripts
COPY simple-debug.sh /simple-debug.sh
COPY test-server-with-livekit.py /test-server.py
RUN chmod +x /simple-debug.sh /test-server.py

# Start with simple bash first, fallback to python if available
CMD ["/simple-debug.sh"]