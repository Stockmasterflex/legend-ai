.PHONY: venv install scan api shots test backtest metrics front up down migrate worker scheduler

PORT ?= 8000
FRONT_PORT ?= 3000
SHOTS_PORT ?= 3010
SHOTS_BASE_URL ?= http://127.0.0.1:$(SHOTS_PORT)

venv:
	python -m venv .venv

install:
	source .venv/bin/activate && pip install -r requirements.txt

scan:
	source .venv/bin/activate && python -m backtest.run_backtest --date today

api:
	@mkdir -p .logs
	@bash -lc 'source .venv/bin/activate; SHOTS_BASE_URL=$(SHOTS_BASE_URL) nohup uvicorn service_api:app --host 0.0.0.0 --reload --port $(PORT) > ./.logs/api.log 2>&1 & echo $$! > ./.logs/api.pid; echo "API started on :$(PORT). Logs: ./.logs/api.log"'

shots:
	@mkdir -p .logs
	@bash -lc 'PORT=$(SHOTS_PORT) nohup node legend-room-screenshot-engine/server.js > ./.logs/shots.log 2>&1 & echo $$! > ./.logs/shots.pid; echo "Shots started on :$(SHOTS_PORT). Logs: ./.logs/shots.log"'

test:
	source .venv/bin/activate && pip install pytest && pytest -q

backtest:
	source .venv/bin/activate && python -m backtest.run_backtest --start 2024-01-01 --end 2024-03-31 --universe simple --provider yfinance

metrics:
	curl -sS "http://127.0.0.1:8000/api/v1/vcp/metrics?start=2024-01-01&end=2024-03-31"

front:
	@mkdir -p .logs
	@bash -lc 'cd kyle-portfolio; PORT=$(PORT) nohup npm run demo > ../.logs/front.log 2>&1 & echo $$! > ../.logs/front.pid; echo "Frontend started on :$(PORT). Logs: ./.logs/front.log"'

migrate:
	@bash -lc 'source .venv/bin/activate; PYTHONPATH=$$(pwd) alembic upgrade head'

worker:
	@bash -lc 'source .venv/bin/activate; OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES nohup python worker.py > ./.logs/worker.log 2>&1 & echo $$! > ./.logs/worker.pid; echo "RQ worker started. Logs: ./.logs/worker.log"'

scheduler:
	@bash -lc 'source .venv/bin/activate; OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES nohup python scheduler.py > ./.logs/scheduler.log 2>&1 & echo $$! > ./.logs/scheduler.pid; echo "Scheduler started. Logs: ./.logs/scheduler.log"'

up:
	@mkdir -p .logs
	@python3 scripts/kill_port.py $(SHOTS_PORT) || true
	@python3 scripts/kill_port.py $(PORT) || true
	@python3 scripts/kill_port.py $(FRONT_PORT) || true
	@$(MAKE) shots SHOTS_PORT=$(SHOTS_PORT)
	@$(MAKE) api PORT=$(PORT) SHOTS_BASE_URL=$(SHOTS_BASE_URL)
	@$(MAKE) front PORT=$(FRONT_PORT)
	@echo "Shots:   http://127.0.0.1:$(SHOTS_PORT)/healthz"
	@echo "API:     http://127.0.0.1:$(PORT)/healthz"
	@echo "Frontend: http://localhost:$(FRONT_PORT)/demo"

down:
	-@test -f ./.logs/api.pid && kill `cat ./.logs/api.pid` 2>/dev/null || true
	-@test -f ./.logs/front.pid && kill `cat ./.logs/front.pid` 2>/dev/null || true
	-@test -f ./.logs/shots.pid && kill `cat ./.logs/shots.pid` 2>/dev/null || true
	-@test -f ./.logs/worker.pid && kill `cat ./.logs/worker.pid` 2>/dev/null || true
	-@test -f ./.logs/scheduler.pid && kill `cat ./.logs/scheduler.pid` 2>/dev/null || true
	-@pkill -f "uvicorn service_api:app" 2>/dev/null || true
	-@pkill -f "next dev" 2>/dev/null || true
	-@pkill -f "node legend-room-screenshot-engine/server.js" 2>/dev/null || true
	-@pkill -f "python worker.py" 2>/dev/null || true
	-@pkill -f "python scheduler.py" 2>/dev/null || true
	-@python3 scripts/kill_port.py $(SHOTS_PORT) || true
	-@python3 scripts/kill_port.py $(PORT) || true
	-@python3 scripts/kill_port.py $(FRONT_PORT) || true
	@echo "Processes stopped."

# Convenience targets for Legend one-shot pack
.PHONY: load check deploy deploy-shots logs logs-shots vercel-status

load:
	@echo "Direnv status:" && direnv status || true
	@echo "(If not allowed, run: direnv allow)"

check:
	./scripts/legend_check.sh

deploy:
	./scripts/legend_deploy.sh

deploy-shots:
	./scripts/legend_deploy.sh shots

logs:
	./scripts/legend_logs.sh api

logs-shots:
	./scripts/legend_logs.sh shots

vercel-status:
	@curl -fsS -H "Authorization: Bearer ${VERCEL_TOKEN}" \
	  "https://api.vercel.com/v6/deployments?app=legend-ai&limit=1" | jq '.deployments[0] | {state,url,createdAt}'

# ===== LEGEND_MAKE_SENTINEL =====
.PHONY: ai top5 ai-deps

ai:
	@python3 scripts/phase4_ai_trading.py --tickers NVDA,AAPL,MSFT,AMD --days 250

top5:
	@echo "Wedge (S&P500, weekly)"
	@curl -s "$(LEGEND_API)/api/v1/scan?pattern=wedge&universe=sp500&timeframe=1wk&limit=1&min_price=0&min_volume=0" \
	  | jq '.results | map({symbol,score,entry,stop,targets,chart_url})' && echo
	@echo "Cup & Handle (NASDAQ-100, daily)"
	@curl -s "$(LEGEND_API)/api/v1/scan?pattern=cup_handle&universe=nasdaq100&limit=1&min_price=0&min_volume=0" \
	  | jq '.results | map({symbol,score,entry,stop,targets,chart_url})'

ai-deps:
	@python3 scripts/ai_deps.py
