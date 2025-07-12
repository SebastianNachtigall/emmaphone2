# EmmaPhone2 Docker Setup

## Development (Local Testing)

Start the full stack for local development:

```bash
# Copy environment variables
cp .env.example .env

# Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Or in background
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

This will start:
- EmmaPhone2 app on http://localhost:3001 and https://localhost:3443
- LiveKit server on ws://localhost:7880
- Redis on localhost:6379

Code changes will auto-reload with nodemon.

## Production (Cloud Deployment)

```bash
# Set production environment variables in .env
docker-compose up -d --build
```

## Stopping Services

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Production
docker-compose down

# Remove volumes (deletes data!)
docker-compose down -v
```

## Database Access

The SQLite database is persisted in the `emmaphone-db` volume and accessible at `/app/data/db/emmaphone.db` inside the container.

## Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f emmaphone
docker-compose logs -f livekit
```