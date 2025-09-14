import argparse
import json
from pathlib import Path
from typing import List
from backtest.simulate import walk_forward, summarize_range
from backtest.simulate import REPORT_ROOT
from backtest.simulate import _load_universe as load_universe  # re-export for CLI
import pandas as pd
from datetime import date

try:
    # Optional import for persistence. Keep CLI working even if DB layer missing.
    from service_db import Base as RunsBase, engine as runs_engine, BacktestRun, SessionLocal as RunsSession
except Exception:
    RunsBase = None
    runs_engine = None
    BacktestRun = None
    RunsSession = None


def scan_once(date_label: str):
    """Compatibility for existing API endpoint.
    Scans default simple universe for a single date (today) using the existing
    ingestion cache and writes a candidates CSV.
    """
    from vcp.vcp_detector import VCPDetector
    from backtest.universe import simple_universe
    from backtest.ingestion import load_prices

    det = VCPDetector()
    rows = []
    for sym in simple_universe():
        df = load_prices(sym)
        sig = det.detect_vcp(df, sym)
        if sig.detected:
            rows.append({
                "date": date_label, "symbol": sym,
                "confidence": sig.confidence_score,
                "pivot": sig.pivot_price,
                "price": float(df["Close"].iloc[-1]),
                "notes": "|".join(sig.notes or [])
            })
    out = REPORT_ROOT / "daily_candidates" / f"{date_label}.csv"
    pd.DataFrame(rows, columns=["date","symbol","confidence","pivot","price","notes"]).to_csv(out, index=False)
    return out


def run_backtest(start: str, end: str, universe_arg: str, provider: str = "yfinance", artifacts_root: Path | None = None) -> Path:
    if provider != "yfinance":
        raise NotImplementedError("Only 'yfinance' provider is implemented in this demo")
    universe = load_universe(universe_arg)
    out_root = artifacts_root if artifacts_root is not None else REPORT_ROOT
    walk_forward(start, end, universe, provider, artifacts_root=out_root)
    summary = summarize_range(start, end, artifacts_root=out_root)
    summary_path = out_root / "summary" / f"summary_{start}_{end}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_obj = {**summary, "start": start, "end": end}
    summary_path.write_text(json.dumps(summary_obj, indent=2))

    # Persist run metadata + KPIs if DB is available
    if BacktestRun is not None and RunsBase is not None and runs_engine is not None and RunsSession is not None:
        try:
            # Ensure table exists
            RunsBase.metadata.create_all(bind=runs_engine)
            db = RunsSession()
            try:
                run = BacktestRun(
                    start=date.fromisoformat(start),
                    end=date.fromisoformat(end),
                    universe=universe_arg,
                    provider=provider,
                    artifacts_root=str(out_root.resolve()),
                    precision_at_10=summary.get("precision_at_10"),
                    precision_at_25=summary.get("precision_at_25"),
                    hit_rate=summary.get("hit_rate"),
                    median_runup=summary.get("median_runup"),
                    num_candidates=summary.get("num_candidates"),
                    num_triggers=summary.get("num_triggers"),
                    num_success=summary.get("num_success"),
                )
                db.add(run)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            # Non-fatal: continue even if persistence fails
            print(f"[warn] failed to persist run: {e}")
    return summary_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe", default="simple")  # or file:<path>
    ap.add_argument("--provider", default="yfinance")
    args = ap.parse_args()
    out = run_backtest(args.start, args.end, args.universe, args.provider)
    print(str(out))
