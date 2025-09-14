FROM node:22-bookworm-slim

WORKDIR /app

# Install Chromium and wget
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium wget ca-certificates fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY package*.json ./
RUN npm ci || npm i

# Copy the rest of the app
COPY . .

# Configure Puppeteer to use system Chromium
ENV PORT=3010 \
    DRY_RUN=1 \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

EXPOSE 3010

CMD ["node","screenshotEngine.js"]
