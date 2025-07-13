FROM livekit/livekit-server:latest

# Expose the necessary ports
EXPOSE 7880
EXPOSE 7881
EXPOSE 50000-60000/udp

# Start LiveKit server with inline configuration
CMD ["livekit-server", \
     "--bind", "0.0.0.0", \
     "--port", "7880", \
     "--rtc-tcp-port", "7881", \
     "--rtc-port-range-start", "50000", \
     "--rtc-port-range-end", "50100", \
     "--keys", "APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"]