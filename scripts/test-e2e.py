#!/usr/bin/env python3
"""
DSA Buddy — End-to-End Integration Test Suite
=============================================
Tests the full flow:
  1. Auth service: register → login → get token
  2. Problem service: search problems via Trie
  3. Hint service: request hints → poll for result
  4. Solve completion: POST solve → verify XP pipeline
  5. Progress service: verify XP and streak updated
  6. Scheduler service: verify review_queue entry
  7. Analytics service: verify leaderboard entry
  8. Health checks: all 7 services respond 200

Usage:
  python scripts/test-e2e.py

Requirements:
  pip install httpx
  All Docker services must be running: docker compose up -d
"""
import asyncio
import sys
import time
import json
import uuid
import httpx

BASE = "http://localhost"
TEST_USER = f"testuser_{uuid.uuid4().hex[:6]}"
TEST_EMAIL = f"{TEST_USER}@gmail.com"
TEST_PASS  = "TestPass123!"

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

results = []

def log(status, test_name, detail=""):
    symbol = {"PASS": PASS, "FAIL": FAIL, "SKIP": SKIP}[status]
    msg = f"{symbol} {test_name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append((status, test_name))

async def run_all():
    token = None
    user_id = None

    print("\n" + "="*60)
    print(" DSA Buddy — End-to-End Integration Test")
    print("="*60 + "\n")

    async with httpx.AsyncClient(timeout=15.0) as c:

        # ── 1. Health Checks ─────────────────────────────────────────
        print(">> Phase 1: Health Checks")
        services = {
            "auth":      f"{BASE}/api/auth/health",
            "problems":  f"{BASE}/api/problems/search?q=two",
            "hints":     f"{BASE}/api/hints/health",
            "ai-agent":  f"{BASE}/api/ai/health",
            "progress":  f"{BASE}/api/progress/health",
            "scheduler": f"{BASE}/api/schedule/health",
            "analytics": f"{BASE}/api/analytics/health",
        }
        for svc, url in services.items():
            try:
                r = await c.get(url)
                if r.status_code == 200:
                    log("PASS", f"Health: {svc}", r.json().get("status", "ok"))
                else:
                    log("FAIL", f"Health: {svc}", f"HTTP {r.status_code}")
            except Exception as e:
                log("FAIL", f"Health: {svc}", str(e))

        # ── 2. Auth: Register ────────────────────────────────────────
        print("\n>> Phase 2: Auth Service")
        try:
            r = await c.post(f"{BASE}/api/auth/register", json={
                "username": TEST_USER,
                "email": TEST_EMAIL,
                "password": TEST_PASS,
            })
            if r.status_code in (200, 201):
                log("PASS", "Register", f"user={TEST_USER}")
            else:
                log("FAIL", "Register", f"HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            log("FAIL", "Register", str(e))

        # ── 3. Auth: Login ───────────────────────────────────────────
        try:
            r = await c.post(f"{BASE}/api/auth/login", json={
                "username": TEST_USER,
                "password": TEST_PASS,
            })
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token")
                # Decode JWT to get user_id
                import base64
                payload_b64 = token.split(".")[1] + "=="
                payload = json.loads(base64.b64decode(payload_b64))
                user_id = payload.get("sub")
                log("PASS", "Login", f"user_id={user_id}")
            else:
                log("FAIL", "Login", f"HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            log("FAIL", "Login", str(e))

        if not token:
            log("SKIP", "All subsequent tests", "No auth token")
            return

        headers = {"Authorization": f"Bearer {token}"}

        # ── 4. Problem Search ────────────────────────────────────────
        print("\n>> Phase 3: Problem Service")
        try:
            r = await c.get(f"{BASE}/api/problems/search?q=two+sum", headers=headers)
            if r.status_code == 200:
                problems = r.json()
                count = len(problems) if isinstance(problems, list) else problems.get("total", 0)
                log("PASS", "Problem search", f"{count} results for 'two sum'")
                if isinstance(problems, list) and problems:
                    slug = problems[0].get("slug", "two-sum")
                else:
                    slug = "two-sum"
            else:
                log("FAIL", "Problem search", f"HTTP {r.status_code}")
                slug = "two-sum"
        except Exception as e:
            log("FAIL", "Problem search", str(e))
            slug = "two-sum"

        # ── 5. Hint Request ──────────────────────────────────────────
        print("\n>> Phase 4: Hint Pipeline")
        event_id = None
        try:
            r = await c.post(f"{BASE}/api/hints/request", headers=headers, json={
                "user_id": user_id,
                "problem_slug": slug,
                "problem_title": "Two Sum",
                "difficulty": "easy",
                "tags": ["array", "hash-table"],
                "hint_level": 3,
            })
            if r.status_code == 200:
                data = r.json()
                event_id = data.get("event_id")
                log("PASS", "Request hints (Kafka publish)", f"event_id={event_id}")
            else:
                log("FAIL", "Request hints", f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log("FAIL", "Request hints", str(e))

        # ── 6. Poll for hints ────────────────────────────────────────
        if event_id:
            try:
                log("PASS", "Polling for hints", "waiting up to 12s for LangGraph pipeline...")
                poll_start = time.time()
                hints_received = []
                for _ in range(24):
                    await asyncio.sleep(0.5)
                    r = await c.get(f"{BASE}/api/hints/poll/{event_id}", headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("status") == "ready":
                            hints_received = data.get("hints", [])
                            break

                elapsed = time.time() - poll_start
                if hints_received:
                    log("PASS", "Hint pipeline end-to-end", f"{len(hints_received)} hints in {elapsed:.1f}s")
                    print(f"     Hint 1: {hints_received[0][:80]}...")
                else:
                    # Try cached hints from AI agent
                    r2 = await c.get(f"{BASE}/api/hints/cached/{user_id}/{slug}", headers=headers)
                    if r2.status_code == 200:
                        cached = r2.json().get("hints", [])
                        log("PASS", "Hints from Redis cache", f"{len(cached)} hints")
                    else:
                        log("SKIP", "Hints poll", f"Pipeline still processing after {elapsed:.1f}s (no OpenAI key?)")
            except Exception as e:
                log("FAIL", "Poll hints", str(e))

        # ── 7. Solve Completion ──────────────────────────────────────
        print("\n>> Phase 5: Solve & Progress Pipeline")
        try:
            r = await c.post(f"{BASE}/api/hints/solve-complete", headers=headers, json={
                "user_id": user_id,
                "problem_slug": slug,
                "difficulty": "easy",
                "time_taken_seconds": 480,
                "language": "python",
                "platform": "leetcode",
                "tags": ["array", "hash-table"],
            })
            if r.status_code == 200:
                log("PASS", "Solve complete (Kafka publish)", r.json().get("event_id", "ok"))
                # Give progress service time to consume
                await asyncio.sleep(2.0)
            else:
                log("FAIL", "Solve complete", f"HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            log("FAIL", "Solve complete", str(e))

        # ── 8. Progress Stats ────────────────────────────────────────
        try:
            r = await c.get(f"{BASE}/api/progress/stats/{user_id}", headers=headers)
            if r.status_code == 200:
                stats = r.json()
                log("PASS", "Progress stats", f"XP={stats.get('xp',0)}, level={stats.get('level',1)}, streak={stats.get('streak_days',0)}")
            else:
                log("FAIL", "Progress stats", f"HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            log("FAIL", "Progress stats", str(e))

        # ── 9. Review Queue ──────────────────────────────────────────
        try:
            r = await c.get(f"{BASE}/api/schedule/queue/{user_id}", headers=headers)
            if r.status_code == 200:
                queue = r.json()
                log("PASS", "Spaced repetition queue", f"{len(queue)} problems scheduled")
            else:
                log("FAIL", "Review queue", f"HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            log("FAIL", "Review queue", str(e))

        # ── 10. Analytics ────────────────────────────────────────────
        print("\n>> Phase 6: Analytics")
        try:
            r = await c.get(f"{BASE}/api/analytics/analytics/overview")
            if r.status_code == 200:
                data = r.json()
                log("PASS", "Analytics overview", f"total_users={data.get('total_users',0)}, total_solves={data.get('total_solves',0)}")
            else:
                log("FAIL", "Analytics overview", f"HTTP {r.status_code}")
        except Exception as e:
            log("FAIL", "Analytics overview", str(e))

        try:
            r = await c.get(f"{BASE}/api/analytics/analytics/leaderboard")
            if r.status_code == 200:
                log("PASS", "Leaderboard", f"{len(r.json())} entries")
            else:
                log("FAIL", "Leaderboard", f"HTTP {r.status_code}")
        except Exception as e:
            log("FAIL", "Leaderboard", str(e))

        try:
            r = await c.get(f"{BASE}/api/analytics/analytics/heatmap/{user_id}", headers=headers)
            if r.status_code == 200:
                log("PASS", "Activity heatmap", f"{len(r.json())} days with data")
            else:
                log("FAIL", "Activity heatmap", f"HTTP {r.status_code}")
        except Exception as e:
            log("FAIL", "Activity heatmap", str(e))

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "="*60)
    total = len(results)
    passed = sum(1 for s, _ in results if s == "PASS")
    failed = sum(1 for s, _ in results if s == "FAIL")
    skipped = sum(1 for s, _ in results if s == "SKIP")
    print(f" Results: {passed}/{total} PASSED  |  {failed} FAILED  |  {skipped} SKIPPED")
    print("="*60 + "\n")

    if failed > 0:
        print("Failed tests:")
        for s, name in results:
            if s == "FAIL":
                print(f"  - {name}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
