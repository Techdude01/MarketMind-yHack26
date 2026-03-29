# Database — how `schema.sql` runs

## Mechanism

The official **PostgreSQL Docker image** runs **initialization scripts** on **first startup only**, when the data directory is empty.

## Where it’s wired

In the repo’s `docker-compose.yml`, the `postgres` service mounts this file into the image’s init directory:

```yaml
- ./db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro
```

## What happens

1. On **first** container creation, Postgres initializes `/var/lib/postgresql/data` (persisted in the Docker named volume `postgres_data`).
2. The image entrypoint executes files under **`/docker-entrypoint-initdb.d/`** in **lexicographic order**. The filename `01-schema.sql` controls order (e.g. runs before `02-…` if you add more init scripts).
3. **`schema.sql`** is executed as SQL against the database created from `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in the root `.env`.

## Important

- **Runs once per new DB cluster.** If `postgres_data` already exists from a previous run, **editing `schema.sql` does not re-run it**. Apply changes manually (e.g. migrations / `psql`), or reset data with `docker compose down -v` then `docker compose up` (this **deletes** volume data).
- The mount is **read-only** (`:ro`); Postgres only needs to read the file.
- **Nothing in Flask or the frontend calls `schema.sql` directly** — initialization is entirely **Postgres container startup** + **this bind mount**.

## Stack context

The backend’s `DATABASE_URL` points at this same Postgres service (hostname `postgres` inside Compose, `localhost:5432` from the host). Tables defined in `schema.sql` are what the app should target for persistence.
