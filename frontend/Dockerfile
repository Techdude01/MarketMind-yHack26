# syntax=docker/dockerfile:1
# Debian slim reduces EIO/rmdir failures during npm installs vs Alpine on some Docker Desktop setups.
FROM node:22

WORKDIR /app

ENV CI=true \
    NPM_CONFIG_UPDATE_NOTIFIER=false

COPY package.json package-lock.json ./

RUN --mount=type=cache,target=/root/.npm \
    npm ci --legacy-peer-deps --no-audit --no-fund

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
