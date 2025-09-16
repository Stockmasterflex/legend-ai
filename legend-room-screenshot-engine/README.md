# Legend Room Screenshot Engine

- PORT: default 3010
- DRY_RUN=1: return a placeholder chart URL without launching a browser
- PUPPETEER_EXECUTABLE_PATH: path to Chromium/Chrome; macOS fallback auto-detected
- CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET: optional upload

Run:
```bash
PORT=3010 DRY_RUN=1 node legend-room-screenshot-engine/screenshotEngine.js
```

