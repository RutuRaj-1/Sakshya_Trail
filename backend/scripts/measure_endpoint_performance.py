"""
SakshyaTrail — Endpoint Latency and Performance Benchmark Script
Non-destructively measures response times (in ms) across representative backend endpoints.
"""
import urllib.request
import time
import json
from typing import List, Tuple

BASE_URL = "http://127.0.0.1:8000"

def run_benchmark():
    # 1. Login as System Admin
    login_data = json.dumps({
        "email": "admin@aicte-india.org",
        "password": "AdminPassword@2026"
    }).encode("utf-8")

    login_req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(login_req, timeout=5) as resp:
            cookie = resp.headers.get("Set-Cookie", "")
            body = json.loads(resp.read().decode("utf-8"))
            token = body.get("access_token", "")
    except Exception as e:
        print(f"Failed to authenticate against {BASE_URL}: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    if cookie:
        headers["Cookie"] = cookie

    endpoints: List[Tuple[str, str]] = [
        ("Health Liveness Probe", "/healthz"),
        ("Health Readiness Probe", "/readyz"),
        ("FDR Instruments Listing", "/api/v1/instruments?limit=20"),
        ("Institutions Listing", "/api/v1/institutions?limit=20"),
        ("Validation Findings Queue", "/api/v1/validation/findings/queue?limit=20"),
        ("Approaching Maturity Surveillance", "/api/v1/lifecycle/monitoring/approaching-maturity"),
        ("Command Center Dashboard Summary", "/api/v1/dashboard/summary"),
        ("Command Center Priority Queue", "/api/v1/dashboard/priority-queue"),
        ("Audit Events Ledger", "/api/v1/audit/events?limit=20"),
        ("Audit Chain Integrity Verification", "/api/v1/audit/integrity"),
        ("Release Requests Listing", "/api/v1/release/requests?limit=20"),
    ]

    print("=" * 78)
    print(" SakshyaTrail Endpoint Response Time Benchmark (5-Run Averaged Latency)")
    print("=" * 78)
    print(f"{'Endpoint Name':<35} | {'HTTP':<4} | {'Latency (ms)':<14} | {'Payload (Bytes)':<14}")
    print("-" * 78)

    for name, path in endpoints:
        latencies = []
        payload_size = 0
        status_code = 0
        for _ in range(5):
            t0 = time.perf_counter()
            req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = res.read()
                    t1 = time.perf_counter()
                    latencies.append((t1 - t0) * 1000)
                    payload_size = len(data)
                    status_code = res.status
            except Exception as ex:
                latencies.append(9999.0)
                status_code = getattr(ex, "code", 500)
                break

        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        print(f"{name:<35} | {status_code:<4} | {avg_lat:>10.2f} ms | {payload_size:>10} B")

    print("=" * 78)
    print("Benchmark completed successfully.")

if __name__ == "__main__":
    run_benchmark()
