# =============================================================================
# DEPENDENCIES STAGE - Install node modules
# =============================================================================
FROM node:20-alpine AS dependencies

# Set working directory
WORKDIR /app

# Install dependencies only (for better layer caching)
# Copy package files first
COPY package*.json ./

# Install dependencies with clean npm cache
# --prefer-offline: Use cache when available
# --no-audit: Skip audit for faster install
# --progress=false: Cleaner output
RUN npm ci --prefer-offline --no-audit --progress=false && \
    npm cache clean --force

# =============================================================================
# DEVELOPMENT STAGE - Runtime with source code
# =============================================================================
FROM node:20-alpine AS development

# Set working directory
WORKDIR /app

# Copy node_modules from dependencies stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy package files
COPY package*.json ./

# Copy source code (excluding test files via .dockerignore)
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 && \
    chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Expose Vite dev server port
EXPOSE 3000

# Health check for Vite dev server
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Start Vite development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
