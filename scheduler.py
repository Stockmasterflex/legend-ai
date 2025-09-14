import os
import time
import redis
from rq_scheduler import Scheduler
from jobs import schedule_daily_standard_run


def main():
    """Background scheduler that enqueues a standard run daily at 16:30 US/Eastern.
    Uses rq-scheduler's cron; no manual datetime math required.
    """
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    conn = redis.from_url(redis_url)
    scheduler = Scheduler(queue_name="legend", connection=conn)

    # Ensure only one cron job exists (idempotent)
    for job in scheduler.get_jobs():
        if getattr(job, "func_name", "").endswith("schedule_daily_standard_run"):
            scheduler.cancel(job)

    scheduler.cron(
        "30 16 * * *",  # 16:30 local (set container TZ to US/Eastern in deploy)
        func=schedule_daily_standard_run,
        queue_name="legend",
        repeat=None,
        use_local_timezone=True,
    )
    print("Scheduler active: daily run at 16:30 local time.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()


