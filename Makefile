.PHONY: venv install scan api test backtest metrics front up down migrate worker scheduler

PORT ?= 8000
FRONT_PORT ?= 3000

venv:
	python -m venv .venv

install:
	source .venv/bin/activate && pip install -r requirements.txt

scan:
	source .venv/bin/activate && python -m backtest.run_backtest --date today

api:
	@mkdir -p .logs
	@bash -lc 'source .venv/bin/activate; nohup uvicorn service_api:app --reload --port $(PORT) > ./.logs/api.log 2>&1 & echo $$! > ./.logs/api.pid; echo "API started on :$(PORT). Logs: ./.logs/api.log"'

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
	@python3 scripts/kill_port.py $(PORT) || true
	@python3 scripts/kill_port.py $(FRONT_PORT) || true
	@$(MAKE) api PORT=$(PORT)
	@$(MAKE) front PORT=$(FRONT_PORT)
	@echo "API:     http://127.0.0.1:$(PORT)/healthz"
	@echo "Frontend: http://localhost:$(FRONT_PORT)/demo"

down:
	-@test -f ./.logs/api.pid && kill `cat ./.logs/api.pid` 2>/dev/null || true
	-@test -f ./.logs/front.pid && kill `cat ./.logs/front.pid` 2>/dev/null || true
	-@test -f ./.logs/worker.pid && kill `cat ./.logs/worker.pid` 2>/dev/null || true
	-@test -f ./.logs/scheduler.pid && kill `cat ./.logs/scheduler.pid` 2>/dev/null || true
	-@pkill -f "uvicorn service_api:app" 2>/dev/null || true
	-@pkill -f "next dev" 2>/dev/null || true
	-@pkill -f "python worker.py" 2>/dev/null || true
	-@pkill -f "python scheduler.py" 2>/dev/null || true
	-@python3 scripts/kill_port.py $(PORT) || true
	-@python3 scripts/kill_port.py $(FRONT_PORT) || true
	@echo "Processes stopped."
