# Legend AI — VCP v1 Loop (Demo)

**What this does**
- Ingests EOD prices (yfinance) with Parquet cache
- Runs VCP detector over a tiny universe
- Writes candidates + outcomes CSVs
- Exposes `/api/v1/vcp/today` via FastAPI

**Quickstart**
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# one-shot scan + label
make scan

# run API on :8000
make api
```

Endpoints
	•	GET /scan/{symbol} → single-symbol VCP JSON
	•	GET /api/v1/vcp/today → runs scan_once(“today”) and returns rows

Next steps
	•	Replace yfinance with Polygon/Tiingo/Norgate in data_provider.py
	•	Expand universe + add ATR stops + precision@K metrics

---

## Python packages

### Create folder tree

legend-ai/
vcp/
backtest/

 (But place everything at repo root as paths below.)

## One-Command Dev

Spin up both the API and the Next.js demo with one command. Logs are written to ./.logs/ .

Start both: make up PORT=8000
FastAPI docs: http://127.0.0.1:8000/docs
Demo dashboard: http://localhost:3000/demo
Stop everything: make down

### Docker (recommended)

For a fully containerized dev stack (API + Redis + RQ worker + scheduler + screenshot engine + frontend):

```
docker compose -f docker-compose.dev.yml up --build
```

Environment variables can be configured via `.env` (copy from `.env.example`).

## Historical runs: persistence and usage

The API persists summary KPIs of backtest windows in a lightweight SQLite DB (`legend_runs.db`). You can list and create runs via API:

List recent runs:

```
curl -s "http://127.0.0.1:8000/api/v1/runs?limit=20" | jq
```

Create a run (summarizes existing reports for the window):

```
curl -s "http://127.0.0.1:8000/api/v1/runs?start=2024-01-02&end=2024-01-31&universe=simple&provider=yfinance" -X POST | jq
```

Fetch metrics for a specific `run_id`:

```
curl -s "http://127.0.0.1:8000/api/v1/vcp/metrics?run_id=1" | jq
```

Fetch candidates for a specific detection day (from reports):

```
curl -s "http://127.0.0.1:8000/api/v1/vcp/candidates?day=2024-01-05" | jq
```

The demo UI now shows a Run selector (defaults to latest) and a Day selector for candidates.

## Local Workflow (one-liners)

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run DB migrations (ensures Alembic imports service_db)
make migrate

# Start API on 8000
make api PORT=8000

# Start worker and scheduler (optional for daily cron)
make worker
make scheduler

# Start frontend on 3000
make front PORT=3000

# All together
make up
```
