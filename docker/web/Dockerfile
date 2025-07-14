# EmmaPhone2 Dockerfile
FROM node:18-alpine AS base

# Set working directory
WORKDIR /app

# Copy package files
COPY web/package*.json ./

# Development stage
FROM base AS development
RUN npm install
COPY web/ .
EXPOSE 3001 3443
CMD ["npm", "run", "dev"]

# Production stage
FROM base AS production
RUN npm install --only=production

# Copy application code
COPY web/src/ ./src/
COPY web/public/ ./public/
COPY web/database/ ./database/

# Create directories for data persistence
RUN mkdir -p /app/data /app/certs

# Expose ports (HTTP and HTTPS)
EXPOSE 3001 3443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3001/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Start the application
CMD ["npm", "start"]