FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
	uv pip install --system -r requirements.txt

COPY . .

ENV FLASK_APP=app
EXPOSE 5001

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5001", "--debug"]
