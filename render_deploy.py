import os

import requests
from dotenv import load_dotenv

load_dotenv()


def update_render_service(service_id: str, repo_url: str) -> requests.Response:
    headers = {
        'Authorization': f'Bearer {os.getenv("RENDER_API_KEY")}',
        'Content-Type': 'application/json'
    }

    data = {
        'repo': repo_url,
        'branch': 'main'
    }

    response = requests.patch(
        f'https://api.render.com/v1/services/{service_id}',
        headers=headers,
        json=data
    )
    return response


if __name__ == "__main__":
    import sys

    service_id = os.getenv("RENDER_SERVICE_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    repo_url = os.getenv("REPO_URL") or (sys.argv[2] if len(sys.argv) > 2 else None)

    if not service_id or not repo_url:
        print("Usage: python render_deploy.py <service_id> <repo_url>  (or set RENDER_SERVICE_ID and REPO_URL env vars)")
        raise SystemExit(2)

    resp = update_render_service(service_id, repo_url)
    print(f"Status: {resp.status_code}")
    print(resp.text)


