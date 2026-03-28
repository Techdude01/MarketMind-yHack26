# MarketMind

Monorepo with a Next.js frontend, Flask API, and PostgreSQL, orchestrated with Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- (Optional) Node.js and Python if you develop services outside Docker

## Quick start

1. Copy environment defaults and adjust if needed:

   ```bash
   cp .env.example .env
   ```

2. Start all services (builds images on first run):

   ```bash
   docker compose up --build
   ```

3. Open the app:

   - **Frontend:** [http://localhost:3000](http://localhost:3000) — use the buttons to call the API.
   - **Backend:** [http://localhost:5000/health](http://localhost:5000/health)
   - **Postgres:** `localhost:5432` (credentials match `.env`)

## Verify database read/write

- In the UI, click **POST /db/write** to insert a row, then **GET /db/read** to see the latest rows (up to 10).
- Or use curl:

  ```bash
  curl -s http://localhost:5000/db/write -H "Content-Type: application/json" \
    -d '{"message":"manual test"}'
  curl -s http://localhost:5000/db/read
  ```

## Data persistence

Postgres files live in the Docker named volume `postgres_data`. Removing containers does not remove this volume unless you run `docker compose down -v`.

## Project layout

- `frontend/` — Next.js app (`NEXT_PUBLIC_API_BASE_URL` points at the Flask API from the browser).
- `backend/` — Flask app; uses `DATABASE_URL` (hostname `postgres` inside Compose).
- `db/schema.sql` — applied automatically on **first** database initialization via `/docker-entrypoint-initdb.d`.

To re-run schema after the DB already exists, apply SQL manually or reset the volume (this deletes data):

```bash
docker compose down -v
docker compose up --build
```
