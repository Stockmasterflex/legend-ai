from __future__ import annotations

import os
from datetime import datetime, date
from typing import Generator

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Date,
    DateTime,
    JSON,
    create_engine,
    UniqueConstraint,
)
from sqlalchemy.orm import sessionmaker, declarative_base


# Use Postgres in production via SERVICE_DATABASE_URL; fallback to local SQLite for dev.
SERVICE_DATABASE_URL = os.getenv("SERVICE_DATABASE_URL", "sqlite:///./legend_runs.db")

engine = create_engine(SERVICE_DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    start = Column(Date, nullable=False, index=True)
    end = Column(Date, nullable=False, index=True)
    universe = Column(String(128), nullable=False, index=True)
    provider = Column(String(64), nullable=False, index=True)

    # Provenance + execution
    status = Column(String(16), nullable=False, default="pending", index=True)  # pending|running|succeeded|failed
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(String(2048), nullable=True)
    detector_version = Column(String(64), nullable=False, default="v1")
    detector_params = Column(JSON, nullable=True)
    universe_spec = Column(JSON, nullable=True)  # resolved list or spec
    code_commit = Column(String(64), nullable=True)
    artifacts_root = Column(String(512), nullable=True)

    # KPIs
    precision_at_10 = Column(Float, nullable=True)
    precision_at_25 = Column(Float, nullable=True)
    hit_rate = Column(Float, nullable=True)
    median_runup = Column(Float, nullable=True)
    num_candidates = Column(Integer, nullable=True)
    num_triggers = Column(Integer, nullable=True)
    num_success = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "start",
            "end",
            "universe",
            "provider",
            "detector_version",
            name="uq_run_idempotency",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "start": self.start.isoformat() if isinstance(self.start, date) else str(self.start),
            "end": self.end.isoformat() if isinstance(self.end, date) else str(self.end),
            "universe": self.universe,
            "provider": self.provider,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "detector_version": self.detector_version,
            "detector_params": self.detector_params,
            "universe_spec": self.universe_spec,
            "code_commit": self.code_commit,
            "artifacts_root": self.artifacts_root,
            "precision_at_10": self.precision_at_10,
            "precision_at_25": self.precision_at_25,
            "hit_rate": self.hit_rate,
            "median_runup": self.median_runup,
            "num_candidates": self.num_candidates,
            "num_triggers": self.num_triggers,
            "num_success": self.num_success,
        }


