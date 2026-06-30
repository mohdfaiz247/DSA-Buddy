import httpx, json, base64, uuid, time, sys

base = 'http://localhost'
user = f'tester_{uuid.uuid4().hex[:5]}'
email = f'{user}@gmail.com'
pw = 'Test1234!'

print('=== DSA Buddy Quick E2E Test ===\n')
results = []

def chk(label, ok, detail=''):
    sym = '[PASS]' if ok else '[FAIL]'
    print(f'{sym} {label}' + (f' - {detail}' if detail else ''))
    results.append(ok)
    return ok

# 1. Health checks
print('>> Phase 1: Health Checks')
for svc, url in [
    ('auth',      f'{base}/api/auth/health'),
    ('hints',     f'{base}/api/hints/health'),
    ('progress',  f'{base}/api/progress/health'),
    ('scheduler', f'{base}/api/schedule/health'),
    ('analytics', f'{base}/api/analytics/health'),
]:
    try:
        r = httpx.get(url, timeout=5)
        chk(f'Health: {svc}', r.status_code == 200,
            r.json().get('status', '?') if r.status_code == 200 else f'HTTP {r.status_code}')
    except Exception as e:
        chk(f'Health: {svc}', False, str(e)[:60])

# 2. Problem search
print('\n>> Phase 2: Problem Service')
try:
    r = httpx.get(f'{base}/api/problems/search?q=binary+search', timeout=5)
    chk('Problem search', r.status_code == 200, f'{len(r.json())} results')
except Exception as e:
    chk('Problem search', False, str(e)[:60])

# 3. Auth
print('\n>> Phase 3: Auth Service')
token = None; uid = None; hdr = {}
try:
    r = httpx.post(f'{base}/api/auth/register', json={'username': user, 'email': email, 'password': pw}, timeout=5)
    chk('Register', r.status_code in (200, 201), user)
except Exception as e:
    chk('Register', False, str(e)[:60])

try:
    r = httpx.post(f'{base}/api/auth/login', json={'username': user, 'password': pw}, timeout=5)
    chk('Login', r.status_code == 200, 'got token' if r.status_code == 200 else r.text[:80])
    if r.status_code == 200:
        token = r.json().get('access_token')
        payload = json.loads(base64.b64decode(token.split('.')[1] + '=='))
        uid = payload['sub']
        hdr = {'Authorization': f'Bearer {token}'}
except Exception as e:
    chk('Login', False, str(e)[:60])

if not token:
    print('\n[SKIP] All remaining tests - no auth token')
    sys.exit(1)

# 4. Hint request (Kafka publish only, no poll)
print('\n>> Phase 4: Hint Pipeline')
try:
    r = httpx.post(f'{base}/api/hints/request', headers=hdr, json={
        'user_id': uid, 'problem_slug': 'two-sum', 'problem_title': 'Two Sum',
        'difficulty': 'easy', 'tags': ['array', 'hash-table'], 'hint_level': 3,
    }, timeout=5)
    if r.status_code == 200:
        eid = r.json().get('event_id', '')
        chk('Hint request (Kafka publish)', True, eid[:20])
    else:
        chk('Hint request', False, f'HTTP {r.status_code}: {r.text[:80]}')
except Exception as e:
    chk('Hint request', False, str(e)[:60])

# 5. Solve complete
print('\n>> Phase 5: Solve & Progress Pipeline')
try:
    r = httpx.post(f'{base}/api/hints/solve-complete', headers=hdr, json={
        'user_id': uid, 'problem_slug': 'two-sum', 'difficulty': 'easy',
        'time_taken_seconds': 300, 'language': 'python',
        'platform': 'leetcode', 'tags': ['array', 'hash-table'],
    }, timeout=5)
    chk('Solve complete (Kafka publish)', r.status_code == 200,
        r.json().get('event_id', '')[:20] if r.status_code == 200 else r.text[:80])
except Exception as e:
    chk('Solve complete', False, str(e)[:60])

# Wait for Kafka consumers to process
print('   (waiting 3s for Kafka consumers...)')
time.sleep(3)

try:
    r = httpx.get(f'{base}/api/progress/stats/{uid}', headers=hdr, timeout=5)
    if r.status_code == 200:
        d = r.json()
        chk('Progress stats', True, f"XP={d.get('xp',0)}, level={d.get('level',1)}, streak={d.get('streak_days',0)}, solves={d.get('total_solves',0)}")
    else:
        chk('Progress stats', False, f'HTTP {r.status_code}: {r.text[:100]}')
except Exception as e:
    chk('Progress stats', False, str(e)[:60])

try:
    r = httpx.get(f'{base}/api/schedule/queue/{uid}', headers=hdr, timeout=5)
    chk('SM-2 review queue', r.status_code == 200, f'{len(r.json())} items' if r.status_code == 200 else r.text[:80])
except Exception as e:
    chk('SM-2 queue', False, str(e)[:60])

try:
    r = httpx.get(f'{base}/api/progress/solves/{uid}', headers=hdr, timeout=5)
    chk('Recent solves list', r.status_code == 200, f'{len(r.json())} solves' if r.status_code == 200 else r.text[:80])
except Exception as e:
    chk('Recent solves', False, str(e)[:60])

# 6. Analytics
print('\n>> Phase 6: Analytics')
try:
    r = httpx.get(f'{base}/api/analytics/overview', timeout=5)
    if r.status_code == 200:
        d = r.json()
        chk('Analytics overview', True, f"users={d.get('total_users',0)}, solves={d.get('total_solves',0)}, tags={len(d.get('top_tags',[]))}")
    else:
        chk('Analytics overview', False, f'HTTP {r.status_code}: {r.text[:80]}')
except Exception as e:
    chk('Analytics overview', False, str(e)[:60])

try:
    r = httpx.get(f'{base}/api/analytics/leaderboard', timeout=5)
    chk('Leaderboard', r.status_code == 200, f'{len(r.json())} ranked users')
except Exception as e:
    chk('Leaderboard', False, str(e)[:60])

try:
    r = httpx.get(f'{base}/api/analytics/heatmap/{uid}', headers=hdr, timeout=5)
    chk('Heatmap', r.status_code == 200, f'{len(r.json())} day records')
except Exception as e:
    chk('Heatmap', False, str(e)[:60])

try:
    r = httpx.get(f'{base}/api/analytics/patterns/{uid}', headers=hdr, timeout=5)
    if r.status_code == 200:
        patterns = r.json()
        chk('DSA patterns', True, ', '.join(p['tag'] for p in patterns[:3]) or 'none yet')
    else:
        chk('DSA patterns', False, f'HTTP {r.status_code}: {r.text[:80]}')
except Exception as e:
    chk('DSA patterns', False, str(e)[:60])

try:
    r = httpx.get(f'{base}/api/analytics/velocity/{uid}', headers=hdr, timeout=5)
    chk('Solve velocity', r.status_code == 200, f'{len(r.json())} week records')
except Exception as e:
    chk('Solve velocity', False, str(e)[:60])

# Summary
total = len(results); passed = sum(results); failed = total - passed
print(f'\n{"="*50}')
print(f' Results: {passed}/{total} PASSED  |  {failed} FAILED')
print('='*50)
if failed:
    sys.exit(1)
