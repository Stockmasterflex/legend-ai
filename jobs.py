from __future__ import annotations

import os
import time
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Dict, Any, List

import redis
from rq import Queue

from service_db import BacktestRun, Base, engine as runs_engine, SessionLocal
from backtest.run_backtest import run_backtest


def get_queue() -> Queue:
    url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    conn = redis.from_url(url)
    return Queue("legend", connection=conn, default_timeout=60 * 60)


def git_commit_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])  # nosec B603
        return out.decode().strip()
    except Exception:
        return "unknown"


def execute_backtest_run(run_id: int) -> Dict[str, Any]:
    """Worker entrypoint to process a BacktestRun row by id."""
    Base.metadata.create_all(bind=runs_engine)
    db = SessionLocal()
    try:
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if run is None:
            return {"status": "not_found", "run_id": run_id}
        # Update status
        run.status = "running"
        run.code_commit = git_commit_short()
        db.commit()

        start_ts = time.time()
        # Compute artifacts root per run
        artifacts_root = Path("backtest/reports/runs") / str(run.id)
        artifacts_root.mkdir(parents=True, exist_ok=True)

        # Execute
        out = run_backtest(
            start=run.start.isoformat(),
            end=run.end.isoformat(),
            universe_arg=run.universe,
            provider=run.provider,
            artifacts_root=artifacts_root,
        )

        # Summaries already written; update fields
        duration_ms = int((time.time() - start_ts) * 1000)
        run.duration_ms = duration_ms
        run.status = "succeeded"
        run.artifacts_root = str(artifacts_root.resolve())
        db.commit()
        return {"status": "succeeded", "run_id": run.id, "duration_ms": duration_ms, "summary_path": str(out)}
    except Exception as e:
        try:
            run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
            if run is not None:
                run.status = "failed"
                run.error_message = str(e)
                db.commit()
        except Exception:
            pass
        return {"status": "failed", "run_id": run_id, "error": str(e)}
    finally:
        db.close()


def enqueue_backtest(start: str, end: str, universe: str, provider: str = "yfinance", detector_version: str = "v1") -> Dict[str, Any]:
    Base.metadata.create_all(bind=runs_engine)
    db = SessionLocal()
    try:
        # Idempotent create-or-get
        existing = (
            db.query(BacktestRun)
            .filter(
                BacktestRun.start == date.fromisoformat(start),
                BacktestRun.end == date.fromisoformat(end),
                BacktestRun.universe == universe,
                BacktestRun.provider == provider,
                BacktestRun.detector_version == detector_version,
            )
            .first()
        )
        if existing:
            run = existing
        else:
            run = BacktestRun(
                start=date.fromisoformat(start),
                end=date.fromisoformat(end),
                universe=universe,
                provider=provider,
                detector_version=detector_version,
                status="pending",
            )
            db.add(run)
            db.commit()
            db.refresh(run)

        q = get_queue()
        q.enqueue(execute_backtest_run, run.id)
        return {"enqueued": True, "run_id": run.id}
    finally:
        db.close()


def schedule_daily_standard_run() -> Dict[str, Any]:
    """Enqueue the standard run for yesterday → today (or last 90 days)."""
    from datetime import datetime, timedelta

    end = datetime.utcnow().date()
    start = end - timedelta(days=90)
    return enqueue_backtest(str(start), str(end), universe="simple", provider="yfinance")


