import os
# macOS fork safety workaround for libraries that touch Objective-C runtime
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
import redis
from rq import Worker, Queue


listen = ["legend"]
redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")


def main():
    conn = redis.from_url(redis_url)
    queues = [Queue(name, connection=conn) for name in listen]
    worker = Worker(queues, connection=conn)
    worker.work()


if __name__ == "__main__":
    main()


