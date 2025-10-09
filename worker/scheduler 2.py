import os
import subprocess
import time

import schedule

WHEN = os.getenv("LEGEND_SCAN_AT", "13:30")  # HH:MM 24h


def run():
    print("[scheduler] running batch scan")
    subprocess.check_call(["python", "worker/scan_batch.py"])


schedule.every().day.at(WHEN).do(run)
print(f"[scheduler] scheduled daily at {WHEN}")
while True:
    schedule.run_pending()
    time.sleep(1)
