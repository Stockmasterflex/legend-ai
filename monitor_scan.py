from legend_ai_backend import Pattern, ScanRun, SessionLocal


def main():
    session = SessionLocal()
    try:
        run = session.query(ScanRun).order_by(ScanRun.started_at.desc()).first()
        patterns = session.query(Pattern).count()
        print("Last scan:")
        if run:
            print(f"  started: {run.started_at}")
            print(f"  finished: {run.finished_at}")
            print(f"  tickers: {run.total_tickers}")
            print(f"  success: {run.success_count}")
            print(f"  failed: {run.failed_count}")
        else:
            print("  no runs found")
        print(f"Patterns in DB: {patterns}")
    finally:
        session.close()


if __name__ == "__main__":
    main()


