# Production web image (S3-10). Build context: ./frontend
# Builds the React app, then serves it with Caddy, which also terminates HTTPS
# and forwards /api and /admin to the backend (one origin, ADR-0001).
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv/app
