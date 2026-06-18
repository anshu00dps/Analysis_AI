# Docker Setup — Analysis AI

## Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY

# 2. Build and start all services
docker compose up --build

# 3. Access the services
# Backend Swagger UI: http://localhost:3000/docs
# Sanitizer Swagger UI: http://localhost:8000/docs
# MongoDB: mongodb://localhost:27017
```

## Services

### MongoDB (mongo:27017)
- **Docker image:** mongo:7
- **Port:** 27017
- **Volume:** `mongo_data` (persists across restarts)
- **Healthcheck:** Uses `mongosh` to ping the server
- **Access locally:** `mongosh mongodb://localhost:27017` or MongoDB Compass

### NER Sanitizer (http://localhost:8000)
- **Docker image:** Built from `Dockerfile.sanitizer`
- **Port:** 8000
- **Volume:** `hf_cache` (1.4GB HuggingFace RoBERTa model cache)
- **Endpoint:** `POST /ner` — accepts `{"text": "..."}`, returns entities + anonymized text
- **Healthcheck:** Checks `/openapi.json` endpoint
- **Start period:** 120s (model download on first run can take time)
- **Access locally:** http://localhost:8000/docs (FastAPI Swagger UI)

### Backend API (http://localhost:3000)
- **Docker image:** Built from `Dockerfile.backend`
- **Port:** 3000
- **Environment:** Reads from `.env` + docker-compose overrides
- **Depends on:** mongo (healthy) + sanitise (healthy)
- **Endpoints:** 11 REST routes for analyses, stages, sanitization, summary, prompts
- **Healthcheck:** Checks `/health` endpoint
- **Access locally:** http://localhost:3000/docs (FastAPI Swagger UI)

## Configuration

### Environment Variables (.env)

**Required:**
- `OPENAI_API_KEY` — Your OpenAI API key (sk-...)

**Optional (defaults shown):**
```env
PORT=3000
ENVIRONMENT=development
MONGODB_URI=mongodb://localhost:27017
DB_NAME=analysisai
SANITIZER_URL=http://localhost:8000/ner
BRD_AGENT_MODEL=gpt-4.1
PROMPT_AGENT_MODEL=gpt-4.1
PLANNING_AGENT_MODEL=gpt-4.1
NOTEBOOK_AGENT_MODEL=gpt-4.1
SUMMARY_AGENT_MODEL=gpt-4.1
```

**Docker Compose Overrides:**
The `docker-compose.yml` overrides service URLs to use in-network names:
- `MONGODB_URI=mongodb://mongo:27017` (not localhost)
- `SANITIZER_URL=http://sanitise:8000/ner` (not localhost)

Local `.env` should use localhost for native (non-Docker) development.

## Common Commands

```bash
# Start all services (builds if needed)
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f sanitise
docker compose logs mongo

# Rebuild images
docker compose up --build

# Stop services
docker compose down

# Stop and remove volumes (cleans database)
docker compose down -v

# Restart a single service
docker compose restart backend

# Execute a command in a container
docker compose exec backend python -m pytest tests/

# Shell into a container
docker compose exec backend bash
docker compose exec mongo mongosh
```

## Troubleshooting

### Backend won't start (MongoDB connection error)
- Ensure mongo is healthy: `docker compose logs mongo`
- Check MongoDB URI is correct: `MONGODB_URI=mongodb://mongo:27017`
- Wait for MongoDB container to fully start (healthcheck takes ~10s)

### Backend won't start (Sanitizer connection error)
- Ensure sanitiser is healthy: `docker compose logs sanitise`
- Check Sanitizer URL is correct: `SANITIZER_URL=http://sanitise:8000/ner`
- Sanitizer can take 2+ minutes on first run (model download)
- Verify HuggingFace cache volume: `docker compose exec sanitise ls /cache/huggingface`

### OPENAI_API_KEY not working
- Verify `.env` file exists and has `OPENAI_API_KEY=sk-...`
- Rebuild backend: `docker compose up --build backend`
- Check backend logs: `docker compose logs backend | grep openai`

### MongoDB data persists but I want a clean slate
```bash
docker compose down -v   # removes mongo_data volume
docker compose up        # recreates fresh database
```

### HuggingFace model cache is large and I want to rebuild
```bash
docker compose down -v   # removes hf_cache volume (1.4GB)
docker compose up        # re-downloads model on sanitiser start
```

## Performance Notes

- **First run:** Sanitiser will download the RoBERTa model (~1.4GB), cached in `hf_cache`
  - This takes 2-10 minutes depending on network and disk
  - Subsequent runs use the cache (instant startup)
- **GPU:** If your Docker daemon has GPU support enabled, the sanitiser will use CUDA (faster inference)
- **Memory:** Plan for ~2GB for the sanitiser (model + inference buffers) + 500MB backend + MongoDB

## Development Workflow

### Local development (without Docker)
```bash
# 1. Start MongoDB and Sanitiser in Docker
docker compose up mongo sanitise

# 2. Run backend locally
uvicorn app.main:app --reload --port 3000
```

### Full Docker testing
```bash
docker compose up
# Edit code
docker compose up --build
```

### Running tests
```bash
# Unit tests (no DB needed)
docker compose exec backend pytest tests/ -v

# With coverage
docker compose exec backend pytest tests/ --cov=app
```

## Production Deployment

For production, consider:
1. Use a managed MongoDB service (Atlas, AWS, etc.) instead of containerized
2. Pin image versions instead of using latest
3. Add environment-specific configs (prod vs. dev)
4. Use a reverse proxy (Nginx) for backend + sanitiser
5. Enable authentication for MongoDB
6. Scale sanitiser horizontally if inference latency becomes a bottleneck
7. Add logging aggregation (ELK, CloudWatch)

Example production docker-compose (conceptual):
```yaml
version: '3.9'
services:
  backend:
    image: analysis-ai:v1.0
    environment:
      MONGODB_URI: mongodb+srv://user:pass@cluster.mongodb.net/analysisai
      ENVIRONMENT: production
    # Add resource limits, security context, etc.
  sanitise:
    image: analysis-ai-sanitizer:v1.0
    replicas: 3  # scale for throughput
```

## Updating Images

After pulling code changes:

```bash
# Rebuild just the backend
docker compose up --build backend

# Rebuild everything
docker compose up --build

# Force rebuild (ignore cache)
docker compose build --no-cache
docker compose up
```
