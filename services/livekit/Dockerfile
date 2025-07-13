FROM livekit/livekit-server:latest

# Install bash for debugging
RUN apk add --no-cache bash

# Copy debug script
COPY debug-with-override.sh /debug-with-override.sh
RUN chmod +x /debug-with-override.sh

# Override ENTRYPOINT completely and use our script
ENTRYPOINT []
CMD ["/debug-with-override.sh"]