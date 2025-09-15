import os
from datetime import date
from pathlib import Path
import pandas as pd

from service_db import Base, engine, SessionLocal, BacktestRun


def ensure_dirs(root: Path) -> None:
    (root / "summary").mkdir(parents=True, exist_ok=True)
    (root / "daily_candidates").mkdir(parents=True, exist_ok=True)
    (root / "outcomes").mkdir(parents=True, exist_ok=True)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create a BacktestRun if none exists
        run = (
            db.query(BacktestRun)
            .order_by(BacktestRun.created_at.desc())
            .first()
        )
        if not run:
            run = BacktestRun(
                start=date(2024, 1, 2),
                end=date(2024, 1, 31),
                universe="simple",
                provider="yfinance",
                status="succeeded",
                precision_at_10=0.42,
                precision_at_25=0.31,
                hit_rate=0.55,
                median_runup=0.12,
                num_candidates=42,
                num_triggers=20,
                num_success=11,
            )
            db.add(run)
            db.commit()
            db.refresh(run)

        # Artifacts root under backtest/reports/runs/{run_id}
        artifacts_root = Path(f"backtest/reports/runs/{run.id}").absolute()
        ensure_dirs(artifacts_root)

        # Sample candidates for two days (expand universe to show more items)
        day1 = artifacts_root / "daily_candidates" / "2024-01-05.csv"
        day2 = artifacts_root / "daily_candidates" / "2024-01-12.csv"
        cand_cols = ["date", "symbol", "confidence", "pivot", "price", "notes"]
        df1 = pd.DataFrame([
            ["2024-01-05", "NVDA", 0.92, 125.4, 128.2, "Tight VCP"] ,
            ["2024-01-05", "MSFT", 0.88, 401.0, 405.3, "Strong base"],
            ["2024-01-05", "AAPL", 0.81, 179.2, 181.4, "Light pullback"],
            ["2024-01-05", "AVGO", 0.79, 880.2, 889.9, "Momentum leader"],
            ["2024-01-05", "META", 0.77, 320.0, 323.1, "Tight action"],
        ], columns=cand_cols)
        df2 = pd.DataFrame([
            ["2024-01-12", "NVDA", 0.90, 130.1, 132.5, "Breakout attempt"],
            ["2024-01-12", "AVGO", 0.84, 890.0, 899.2, "High momentum"],
            ["2024-01-12", "TSLA", 0.72, 252.0, 255.3, "VCP forming"],
            ["2024-01-12", "AMD", 0.74, 112.5, 114.2, "Chip peer"],
        ], columns=cand_cols)
        df1.to_csv(day1, index=False)
        df2.to_csv(day2, index=False)

        # Sample outcomes aligned to detection dates
        out_cols = [
            "date_detected","symbol","trigger_date","triggered","success","exit_date","max_runup_30d","max_drawdown_30d","r_multiple"
        ]
        out1 = pd.DataFrame([
            ["2024-01-05","NVDA","2024-01-06",1,1,"2024-01-20",0.24,0.06,0.18],
            ["2024-01-05","MSFT","2024-01-07",1,0,"2024-01-25",0.08,0.05,0.01],
        ], columns=out_cols)
        out2 = pd.DataFrame([
            ["2024-01-12","NVDA","2024-01-13",1,1,"2024-01-27",0.31,0.07,0.22],
            ["2024-01-12","AVGO","2024-01-13",1,1,"2024-01-27",0.18,0.04,0.12],
            ["2024-01-12","TSLA","2024-01-13",1,0,"2024-01-25",0.09,0.06,0.03],
            ["2024-01-12","AMD","2024-01-13",1,1,"2024-01-28",0.15,0.05,0.10],
        ], columns=out_cols)
        (artifacts_root / "outcomes" / "2024-01-05_outcomes.csv").write_text(out1.to_csv(index=False))
        (artifacts_root / "outcomes" / "2024-01-12_outcomes.csv").write_text(out2.to_csv(index=False))

        # Update run with artifacts_root
        run.artifacts_root = str(artifacts_root)
        db.add(run)
        db.commit()

        print({
            "seeded_run_id": run.id,
            "artifacts_root": run.artifacts_root,
            "days": ["2024-01-05","2024-01-12"],
        })
    finally:
        db.close()


if __name__ == "__main__":
    main()


