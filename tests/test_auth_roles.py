"""Quick test for role-based auth endpoints."""
import requests
import json

BASE = "http://localhost:8000"

def check_login(username, password, expected_role):
    r = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password})
    data = r.json()
    ok = r.status_code == 200 and data.get("role") == expected_role
    print(f"  {'✓' if ok else '✗'} [{r.status_code}] login({username}) → role={data.get('role','?')} (expected {expected_role})")
    return data.get("access_token") if ok else None


def check_me(token, expected_role):
    r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
    data = r.json()
    ok = r.status_code == 200 and data.get("role") == expected_role
    print(f"  {'✓' if ok else '✗'} /auth/me → role={data.get('role','?')} (expected {expected_role})")


def check_admin_endpoint(token, is_admin):
    r = requests.get(f"{BASE}/admin/hot-topics", headers={"Authorization": f"Bearer {token}"})
    expected_status = 200 if is_admin else 403
    ok = r.status_code == expected_status
    detail = r.json().get("detail", "") if r.status_code != 200 else "access granted"
    print(f"  {'✓' if ok else '✗'} /admin/hot-topics [{r.status_code}] → {detail}")


def check_bad_login():
    r = requests.post(f"{BASE}/auth/login", json={"username": "hacker", "password": "wrong"})
    ok = r.status_code == 401
    print(f"  {'✓' if ok else '✗'} bad login → {r.status_code} {r.json().get('detail','')}")


if __name__ == "__main__":
    print("\n=== Role-Based Auth Tests ===\n")

    print("1. Login tests:")
    admin_token = check_login("admin", "admin123", "admin")
    user_token = check_login("user", "user123", "user")
    check_bad_login()

    print("\n2. /auth/me role check:")
    if admin_token:
        check_me(admin_token, "admin")
    if user_token:
        check_me(user_token, "user")

    print("\n3. Admin endpoint access control:")
    if admin_token:
        print("  Admin token:")
        check_admin_endpoint(admin_token, is_admin=True)
    if user_token:
        print("  User token (should 403):")
        check_admin_endpoint(user_token, is_admin=False)

    print("\n=== Done ===")
