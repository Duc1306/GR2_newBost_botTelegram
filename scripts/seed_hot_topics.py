"""
Seed hot topics into MongoDB.

Usage:
    python scripts/seed_hot_topics.py

Requires the API to be running at http://localhost:8000
(uses admin credentials to call POST /admin/hot-topics/seed)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from src.config import ADMIN_USERNAME, ADMIN_PASSWORD

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def main():
    # 1. Login to get JWT token
    resp = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Seed hot topics
    seed_resp = requests.post(
        f"{API_BASE}/admin/hot-topics/seed",
        headers=headers,
        timeout=10,
    )
    seed_resp.raise_for_status()
    result = seed_resp.json()
    print(f"[seed_hot_topics] Done: {result}")


if __name__ == "__main__":
    main()
