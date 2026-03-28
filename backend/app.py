import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from db import get_connection

load_dotenv()

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": os.getenv("CORS_ORIGINS", "*")}},
)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/db/health")
def db_health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify(status="ok", database="reachable")
    except Exception as e:
        return jsonify(status="error", detail=str(e)), 503


@app.post("/db/write")
def db_write():
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    if message is None or not isinstance(message, str) or not message.strip():
        return jsonify(error='JSON body must include a non-empty string "message"'), 400

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO healthcheck (message) VALUES (%s) RETURNING id, message, created_at",
                (message.strip(),),
            )
            row = cur.fetchone()
        conn.commit()

    created_at = row[2]
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    return jsonify(id=row[0], message=row[1], created_at=created_at)


@app.get("/db/read")
def db_read():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, message, created_at FROM healthcheck ORDER BY id DESC LIMIT 10"
            )
            rows = cur.fetchall()

    out = []
    for rid, msg, created_at in rows:
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        out.append({"id": rid, "message": msg, "created_at": created_at})

    return jsonify(rows=out)


@app.get("/")
def home():
    return jsonify(status="backend running")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
