# Use an official Node.js runtime as a parent image
FROM node:20-alpine AS builder

WORKDIR /app

# Create a directory for the pnpm store and configure pnpm to use it

ENV PNPM_HOME="/pnpm"

ENV PATH="$PNPM_HOME:$PATH"
RUN npm install -g pnpm

# Copy package.json and pnpm-lock.yaml from the frontend context
COPY package.json pnpm-lock.yaml ./

ENV CI=true

RUN pnpm install --frozen-lockfile

# Copy the rest of the frontend application code
COPY . .

# Build the Next.js application
RUN pnpm build

# --- Production Stage ---
FROM node:20-alpine AS runner

# Set environment variables
ENV NODE_ENV=production
# Set NEXT_TELEMETRY_DISABLED to disable telemetry
ENV NEXT_TELEMETRY_DISABLED=1

# Set the working directory
WORKDIR /app

# Copy necessary files from the builder stage
COPY --from=builder /app/public ./public

# Configure pnpm store and copy from builder stage
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN npm install -g pnpm




# Copy package.json and pnpm-lock.yaml for offline install
COPY package.json pnpm-lock.yaml ./

# Install project dependencies in offline mode
RUN pnpm install --frozen-lockfile

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Expose the port the app runs on
EXPOSE 3000

# Set the command to run the application
CMD ["node", "server.js"]
