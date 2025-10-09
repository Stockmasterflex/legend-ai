import json
import os
from datetime import datetime

from legend_ai_backend import Pattern, SessionLocal, Stock


def export_scan_results(output_dir: str = os.path.join('data', 'exports')) -> str:
    os.makedirs(output_dir, exist_ok=True)
    session = SessionLocal()
    try:
        patterns = (
            session.query(Pattern)
            .filter(Pattern.status == "active", Pattern.pattern_type == "VCP")
            .all()
        )
        symbols = list({p.symbol for p in patterns})
        stocks = session.query(Stock).filter(Stock.symbol.in_(symbols)).all() if symbols else []
        stock_map = {s.symbol: s for s in stocks}

        results = []
        for p in patterns:
            s = stock_map.get(p.symbol)
            results.append({
                "symbol": p.symbol,
                "name": (s.name if s and s.name else p.symbol),
                "sector": (s.sector if s and s.sector else "Unknown"),
                "pattern_type": p.pattern_type,
                "confidence": float(p.confidence or 0.0),
                "pivot_price": float(p.pivot_price or 0.0),
                "stop_loss": float(p.stop_loss or 0.0),
                "current_price": float(s.current_price or 0.0) if s else 0.0,
                "days_in_pattern": int(p.days_in_pattern or 0),
                "rs_rating": int(s.rs_rating or 0) if s else 0,
                "detected_at": p.detected_at.isoformat() if p.detected_at else None,
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)

        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        out_path = os.path.join(output_dir, f'vcp_results_{ts}.json')
        with open(out_path, 'w') as f:
            json.dump({
                "generated_at": datetime.utcnow().isoformat(),
                "count": len(results),
                "results": results
            }, f, indent=2)

        latest_path = os.path.join(output_dir, 'vcp_results_latest.json')
        with open(latest_path, 'w') as f:
            json.dump({
                "generated_at": datetime.utcnow().isoformat(),
                "count": len(results),
                "results": results
            }, f, indent=2)

        print(f"Exported {len(results)} results to {out_path}")
        return out_path
    finally:
        session.close()


if __name__ == '__main__':
    export_scan_results()
