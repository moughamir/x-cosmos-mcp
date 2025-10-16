# Use an official Node.js runtime as a parent image
FROM node:20-alpine AS builder

# Set the working directory in the container
WORKDIR /app

# Copy package.json and pnpm-lock.yaml from the frontend context
COPY package.json pnpm-lock.yaml ./

# Install pnpm globally
RUN npm install -g pnpm

# Copy the rest of the frontend application code
COPY . .

ENV CI=true

# Install project dependencies
RUN pnpm install --frozen-lockfile

# Build the Next.js application
RUN pnpm build

# --- Production Stage ---
FROM node:20-alpine AS runner

# Set environment variables
ENV NODE_ENV=production
# Set NEXT_TELEMETRY_DISABLED to disable telemetry
ENV NEXT_TELEMETRY_DISABLED 1

# Set the working directory
WORKDIR /app

# Copy necessary files from the builder stage
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Expose the port the app runs on
EXPOSE 3000

# Set the command to run the application
CMD ["node", "server.js"]
