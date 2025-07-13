FROM alpine:latest

# Install basic tools and Python for a simple server
RUN apk add --no-cache python3 curl bash

# Expose the necessary ports
EXPOSE 7880

# Create a simple test server
COPY test-server.py /test-server.py
RUN chmod +x /test-server.py

# Start test server
CMD ["python3", "/test-server.py"]