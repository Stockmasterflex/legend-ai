import re
import sys
from pathlib import Path


def fail(msg: str) -> None:
    print(f"[doctor_render] {msg}")
    sys.exit(1)


def main() -> None:
    p = Path("render.yaml")
    if not p.exists():
        print("[doctor_render] render.yaml not found; skipping")
        return

    text = p.read_text()

    # Service type web
    if "type: web" not in text:
        fail("render.yaml must configure a web service")

    # healthCheckPath
    if "healthCheckPath" not in text or "/healthz" not in text:
        fail("render.yaml must set healthCheckPath: '/healthz'")

    # No hard-coded port
    if re.search(r":8000\b", text):
        fail("render.yaml must not reference :8000 anywhere")

    # No dockerCommand/startCommand overriding CMD
    if "startCommand:" in text or "dockerCommand:" in text:
        fail("render.yaml must not override uvicorn CMD in Dockerfile (remove startCommand/dockerCommand)")

    print("[doctor_render] OK")


if __name__ == "__main__":
    main()


