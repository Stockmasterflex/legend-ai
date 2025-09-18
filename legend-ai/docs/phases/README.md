# Phases – Legend AI

This section links the imported high-level plans to what exists in this repository and what remains as future work.

Phase 1 – Automated Stock Analysis Platform (Imported)
- Docs: ../imports/phase-1-automated-stock-analysis-platform-setup-guide.md
- Scope (import): n8n workflows, Google Sheets storage, Streamlit dashboard
- Status (repo): Not implemented here; this repo uses FastAPI + Next.js instead of n8n/Streamlit
- Recommendation: Track n8n/Sheets flows in a separate repo or future module; keep this repo focused on API+frontend

Phase 2 – Data Collection in n8n (Imported)
- Docs: ../imports/phase-2-data-collection-in-n8n.md
- Scope (import): AlphaVantage/yfinance ingestion → Google Sheets, robust retries, scheduling
- Status (repo): Backend uses yfinance directly inside the API; no n8n integration baked in
- Recommendation: Provide optional Webhooks in this API to ingest external pipelines later

Phase 3 – Technical Analysis Workflow (Imported)
- Docs: ../imports/phase-3-technical-analysis-workflow.md
- Scope (import): Indicators, signals, backtesting logic, persistence, dashboards
- Status (repo): Implemented in indicators/, signals/, backtest/ with API exposure and demo UI
- Next: Expand indicators and signals coverage; add tests and docstrings

Phase 4 – Advanced AI Trading Implementation (Imported)
- Docs: ../imports/phase-4-advanced-ai-trading-implementation.md
- Scope (import): AI analysis, execution readiness, improved data feeds
- Status (repo): Baseline endpoints with sample fallbacks; no trading execution; AI summarization not exposed yet
- Next: Add analysis summary endpoint and consider a provider abstraction for premium data
