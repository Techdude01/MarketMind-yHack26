CREATE TABLE IF NOT EXISTS healthcheck (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
