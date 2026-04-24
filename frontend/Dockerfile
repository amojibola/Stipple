FROM node:20-alpine AS base

WORKDIR /app

RUN addgroup -S stipple && adduser -S stipple -G stipple

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps
COPY package*.json ./
RUN npm ci

# ── Dev target (used by docker-compose.yml) ───────────────────────────────────
FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN chown -R stipple:stipple /app
USER stipple
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ── Builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── Runner (production — used by docker-compose.prod.yml) ─────────────────────
FROM base AS runner
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

RUN chown -R stipple:stipple /app
USER stipple

EXPOSE 3000
CMD ["node", "server.js"]
