#!/usr/bin/env python3
"""
Render service doctor for legend-api.

Inspects service config, recent deploys, and can trigger a clear-cache redeploy.
Requires RENDER_API_KEY env var; graceful fallback if missing.
"""

import os
import sys
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("[render_doctor] requests module not found. Install with: pip install requests")
    sys.exit(1)


API_BASE = "https://api.render.com/v1"
API_KEY = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "legend-api")


def get_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}


def list_services() -> List[Dict[str, Any]]:
    r = requests.get(f"{API_BASE}/services", headers=get_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def get_service(service_id: str) -> Dict[str, Any]:
    r = requests.get(f"{API_BASE}/services/{service_id}", headers=get_headers(), timeout=10)
    r.raise_for_status()
    data = r.json()
    # API returns service directly, not nested
    return data if "name" in data else data.get("service", {})


def list_deploys(service_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    r = requests.get(
        f"{API_BASE}/services/{service_id}/deploys",
        params={"limit": limit},
        headers=get_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def trigger_deploy(service_id: str, clear_cache: bool = True) -> Dict[str, Any]:
    payload = {"clearCache": "clear"} if clear_cache else {}
    r = requests.post(
        f"{API_BASE}/services/{service_id}/deploys",
        json=payload,
        headers=get_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def find_service_by_name(name: str) -> Optional[str]:
    services = list_services()
    for svc in services:
        s = svc.get("service", {})
        if s.get("name") == name:
            return s.get("id")
    return None


def print_manual_checklist():
    print("\n[render_doctor] RENDER_API_KEY not set. Manual operator checklist:\n")
    print("  1. Render → legend-api → Settings → Build & Deploy:")
    print("     - Repository: Stockmasterflex/legend-ai-dashboard")
    print("     - Branch: main")
    print("     - Auto-Deploy: ON")
    print("  2. Health Check:")
    print("     - Path: /healthz")
    print("     - Timeout: 200s")
    print("  3. Manual Deploy → 'Clear build cache & deploy'")
    print("  4. Events: confirm probe has no :8000; logs show uvicorn on non-8000 port")
    print("  5. Verify:")
    print("     - curl -s https://legend-api.onrender.com/healthz")
    print("     - curl -s https://legend-api.onrender.com/readyz")
    print("     - curl -s 'https://legend-api.onrender.com/v1/meta/status'")
    print("")


def main():
    redeploy = "--redeploy" in sys.argv

    if not API_KEY:
        print_manual_checklist()
        sys.exit(0)

    # Find service ID
    sid = SERVICE_ID
    if not sid:
        print(f"[render_doctor] Searching for service: {SERVICE_NAME}...")
        sid = find_service_by_name(SERVICE_NAME)
        if not sid:
            print(f"[render_doctor] Service '{SERVICE_NAME}' not found.")
            print("[render_doctor] Available services:")
            for svc in list_services():
                s = svc.get("service", {})
                print(f"  - {s.get('name')} ({s.get('id')}) type={s.get('type')}")
            sys.exit(1)

    # Fetch service details
    service = get_service(sid)
    repo = service.get("serviceDetails", {}).get("repo")
    branch = service.get("serviceDetails", {}).get("branch", "N/A")
    auto_deploy = service.get("serviceDetails", {}).get("autoDeploy", "N/A")
    health_path = service.get("serviceDetails", {}).get("healthCheckPath", "N/A")

    print(f"\n[render_doctor] Service: {service.get('name')} ({sid})")
    print(f"  Repo: {repo} @ {branch}")
    print(f"  Auto-Deploy: {auto_deploy}")
    print(f"  Health Check: {health_path}")

    # Fetch recent deploys
    deploys = list_deploys(sid, limit=5)
    print(f"\n[render_doctor] Last {len(deploys)} deploys:")
    for d in deploys:
        deploy = d.get("deploy", {})
        created = deploy.get("createdAt", "N/A")
        status = deploy.get("status", "N/A")
        commit_id = deploy.get("commit", {}).get("id", "N/A")[:7]
        summary = deploy.get("commit", {}).get("message", "").split("\n")[0][:60]
        print(f"  - {created}  {status}  {commit_id}  {summary}")

    # Trigger redeploy if requested
    if redeploy:
        print("\n[render_doctor] Triggering clear-cache redeploy...")
        result = trigger_deploy(sid, clear_cache=True)
        new_deploy = result.get("deploy", {})
        print(f"  Deploy triggered: {new_deploy.get('id')} status={new_deploy.get('status')}")
        print("  Monitor at: https://dashboard.render.com")
    else:
        print("\n[render_doctor] Run with --redeploy to trigger a clear-cache deploy.")

    print("")


if __name__ == "__main__":
    main()

