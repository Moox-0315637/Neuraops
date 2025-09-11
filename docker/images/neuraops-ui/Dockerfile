# ==============================================================================
# NeuraOps UI - Docker Multi-Stage Build
# Modern Next.js 15 + TypeScript + Tailwind CSS Production Image
# ==============================================================================

# Base image with Node.js 18+ (Alpine for smaller size)
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine
# to understand why libc6-compat might be needed.
# hadolint ignore=DL3018
RUN apk add --no-cache libc6-compat

# Copy package files
COPY neuraops-ui/package.json ./
COPY neuraops-ui/package-lock.json* ./

# Install ALL dependencies (including devDependencies for build)
RUN \
  if [ -f package-lock.json ]; then \
    echo "Installing all dependencies with npm ci..." && \
    npm ci; \
  else \
    echo "Installing all dependencies with npm install..." && \
    npm install; \
  fi

# ==============================================================================
# Builder stage - Build the Next.js application
# ==============================================================================
FROM base AS builder
WORKDIR /app

# Build argument to choose environment file (default to local for Docker development)
ARG ENV_FILE=.env.local

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application source code (excluding node_modules)
COPY neuraops-ui/src ./src
COPY neuraops-ui/public ./public
COPY neuraops-ui/next.config.js ./
COPY neuraops-ui/tsconfig.json ./
COPY neuraops-ui/tailwind.config.ts ./
COPY neuraops-ui/postcss.config.js ./
COPY neuraops-ui/.eslintrc.json ./
COPY neuraops-ui/package.json ./

# Copy the specified environment file (default: .env.local for Docker dev)
COPY neuraops-ui/${ENV_FILE} ./${ENV_FILE}

# Environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Build the Next.js application with standalone output
RUN npm run build

# ==============================================================================
# Production dependencies stage - Install only production deps
# ==============================================================================
FROM base AS prod-deps
WORKDIR /app

# hadolint ignore=DL3018
RUN apk add --no-cache libc6-compat

# Copy package files
COPY neuraops-ui/package.json ./
COPY neuraops-ui/package-lock.json* ./

# Install ONLY production dependencies
RUN \
  if [ -f package-lock.json ]; then \
    echo "Installing production dependencies with npm ci..." && \
    npm ci --only=production; \
  else \
    echo "Installing production dependencies with npm install..." && \
    npm install --production; \
  fi

# ==============================================================================
# Production stage - Final runtime image
# ==============================================================================
FROM base AS runner
WORKDIR /app

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Set environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# NeuraOps specific environment variables
ENV NEURAOPS_API_URL=http://localhost:8000
ENV NEURAOPS_WS_URL=ws://localhost:8000
ENV NEURAOPS_ENV=production

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy public assets (includes site.webmanifest)
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Expose port
EXPOSE 3000

# Switch to non-root user
USER nextjs

# Start the Next.js application
CMD ["node", "server.js"]

