from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from vcp.vcp_detector import VCPDetector
from backtest.ingestion import load_prices
from backtest.labeling import breakout_trigger, evaluate_outcome
from backtest.metrics import precision_at_k, hit_rate, median_runup
from backtest.universe import simple_universe


REPORT_ROOT = Path("backtest/reports")
(REPORT_ROOT / "daily_candidates").mkdir(parents=True, exist_ok=True)
(REPORT_ROOT / "outcomes").mkdir(parents=True, exist_ok=True)
(REPORT_ROOT / "summary").mkdir(parents=True, exist_ok=True)


def _date_range(start: str, end: str) -> List[str]:
    s = datetime.fromisoformat(start).date()
    e = datetime.fromisoformat(end).date()
    days = []
    cur = s
    while cur <= e:
        days.append(str(cur))
        cur = cur + timedelta(days=1)
    return days


def _load_universe(arg: str) -> List[str]:
    if arg == "simple":
        return simple_universe()
    if arg.startswith("file:"):
        p = Path(arg.split(":", 1)[1])
        df = pd.read_csv(p)
        col = None
        for c in df.columns:
            if c.lower() == "symbol":
                col = c
                break
        if col is None:
            raise ValueError("Universe CSV must have a 'symbol' column")
        return [str(s).upper() for s in df[col].dropna().unique().tolist()]
    raise ValueError("--universe must be 'simple' or 'file:<path>'")


def walk_forward(start: str, end: str, universe: List[str], provider: str = "yfinance", artifacts_root: Path | None = None) -> Dict[str, Path]:
    det = VCPDetector()
    # Preload price data once per symbol (cached via Parquet in load_prices)
    price_map: Dict[str, pd.DataFrame] = {}
    for sym in universe:
        try:
            df = load_prices(sym)
            # Ensure Date as datetime and sorted
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date").reset_index(drop=True)
            price_map[sym] = df
        except Exception as e:
            # minimal logging; continue
            print(f"[warn] failed to load {sym}: {e}")

    results = {"candidates": [], "outcomes": []}
    run_root = artifacts_root if artifacts_root is not None else REPORT_ROOT
    (run_root / "daily_candidates").mkdir(parents=True, exist_ok=True)
    (run_root / "outcomes").mkdir(parents=True, exist_ok=True)
    (run_root / "summary").mkdir(parents=True, exist_ok=True)

    for day in _date_range(start, end):
        daily_rows = []
        for sym, df in price_map.items():
            # Subset up to day
            sub = df[df["Date"] <= day]
            if len(sub) < 200:
                continue
            try:
                sig = det.detect_vcp(sub, sym)
                if sig.detected:
                    daily_rows.append({
                        "date": day,
                        "symbol": sym,
                        "confidence": sig.confidence_score,
                        "pivot": sig.pivot_price,
                        "price": float(sub["Close"].iloc[-1]),
                        "notes": "|".join(sig.notes or [])
                    })
            except Exception as e:
                print(f"[warn] detect failed {sym}@{day}: {e}")

        cand_path = run_root / "daily_candidates" / f"{day}.csv"
        pd.DataFrame(daily_rows, columns=["date","symbol","confidence","pivot","price","notes"]).to_csv(cand_path, index=False)
        results["candidates"].append(cand_path)

        # Label outcomes for this day
        out_rows = []
        if len(daily_rows) > 0:
            for r in daily_rows:
                sym = r["symbol"]
                pivot = float(r["pivot"]) if r["pivot"] is not None else None
                if pivot is None:
                    continue
                df = price_map[sym]
                trig, tdate = breakout_trigger(df, pivot)
                if not trig:
                    continue
                # locate start index
                idx_list = df.index[df["Date"] == pd.to_datetime(tdate)].tolist()
                if not idx_list:
                    continue
                start_idx = int(idx_list[0])
                # define stop (last 10-day low or 8% below pivot)
                recent_low = float(df["Low"].iloc[max(0, start_idx-10):start_idx].min()) if start_idx > 0 else float(df["Low"].iloc[:start_idx+1].min())
                stop = max(recent_low, pivot * 0.92)
                success, exit_date = evaluate_outcome(df, start_idx, pivot, stop)
                # 30-day window stats
                end_idx = min(start_idx + 30, len(df)-1)
                window = df.iloc[start_idx:end_idx+1]
                max_high = float(window["High"].max())
                min_low = float(window["Low"].min())
                max_runup = (max_high - pivot) / max(pivot, 1e-6)
                max_drawdown = (pivot - min_low) / max(pivot, 1e-6)
                R = max(pivot - stop, 1e-6)
                r_multiple = (max_high - pivot) / R

                out_rows.append({
                    "date_detected": day,
                    "symbol": sym,
                    "trigger_date": str(tdate),
                    "triggered": 1,
                    "success": 1 if success else 0,
                    "exit_date": str(exit_date) if exit_date is not None else None,
                    "max_runup_30d": max_runup,
                    "max_drawdown_30d": max_drawdown,
                    "r_multiple": r_multiple,
                })

        out_path = run_root / "outcomes" / f"{day}_outcomes.csv"
        pd.DataFrame(out_rows, columns=[
            "date_detected","symbol","trigger_date","triggered","success","exit_date",
            "max_runup_30d","max_drawdown_30d","r_multiple"
        ]).to_csv(out_path, index=False)
        results["outcomes"].append(out_path)

    return results


def summarize_range(start: str, end: str, artifacts_root: Path | None = None) -> Dict[str, float]:
    # load candidates and outcomes in range
    root = artifacts_root if artifacts_root is not None else REPORT_ROOT
    cand_dir = root / "daily_candidates"
    out_dir = root / "outcomes"
    cdfs = []
    odfs = []
    for p in sorted(cand_dir.glob("*.csv")):
        d = p.stem
        if start <= d <= end:
            df = pd.read_csv(p)
            if len(df) > 0:
                cdfs.append(df)
    for p in sorted(out_dir.glob("*_outcomes.csv")):
        d = p.stem.replace("_outcomes", "")
        if start <= d <= end:
            df = pd.read_csv(p)
            if len(df) > 0:
                odfs.append(df)
    cands = pd.concat(cdfs, ignore_index=True) if cdfs else pd.DataFrame(columns=["date","symbol","confidence","pivot","price","notes"])
    outs = pd.concat(odfs, ignore_index=True) if odfs else pd.DataFrame(columns=["date_detected","symbol","trigger_date","triggered","success","exit_date","max_runup_30d","max_drawdown_30d","r_multiple"])

    summary = {
        "precision_at_10": precision_at_k(cands, outs, 10),
        "precision_at_25": precision_at_k(cands, outs, 25),
        "hit_rate": hit_rate(outs),
        "median_runup": median_runup(outs),
        "num_candidates": int(len(cands)),
        "num_triggers": int(len(outs)),
        "num_success": int((outs["success"] == 1).sum()) if len(outs) else 0,
    }
    return summary

