FROM livekit/livekit-server:latest

# Expose the necessary ports
EXPOSE 7880
EXPOSE 7881
EXPOSE 50000-60000/udp

# Add debugging script
COPY debug-start.sh /debug-start.sh
RUN chmod +x /debug-start.sh

# Start with debugging
CMD ["/debug-start.sh"]