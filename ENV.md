# Environment Configuration

Create a `.env` file at the repository root. Do not commit it. Use `.env.example` as a reference.

Required variables:

Slack / Bot
- SLACK_BOT_TOKEN=
- SLACK_APP_TOKEN=
- OPENAI_API_KEY=
- FOREMAN_SCHEDULE_CHANNEL_ID=  # optional for scheduled reports

GitHub (optional for PR links)
- GITHUB_USERNAME=
- GITHUB_REPO=

Render / Deploy
- RENDER_TOKEN=
- API_SERVICE_ID=
- SHOTS_SERVICE_ID=

Vercel / Frontend
- VERCEL_DEPLOY_HOOK_URL=
- VERCEL_TOKEN=  # optional; used to poll API state
- NEXT_PUBLIC_VCP_API_BASE=https://legend-api.onrender.com

Sanity CMS (if applicable to `kyle-portfolio`)
- SANITY_PROJECT_ID=
- SANITY_DATASET=
- SANITY_API_READ_TOKEN=

Cloudinary (for legend-shots)
- CLOUDINARY_CLOUD_NAME=
- CLOUDINARY_API_KEY=
- CLOUDINARY_API_SECRET=

Backend service
- SERVICE_DATABASE_URL=
- REDIS_URL=
- ALLOWED_ORIGINS=
- ALLOWED_ORIGIN_REGEX=
- VCP_PROVIDER=

Notes:
- `.env` is ignored via `.gitignore`.
- Set these as Render/Vercel env vars in production; `.env` is for local dev.
