/**
 * DSA Buddy Service Worker (MV3 background script)
 * Handles:
 *   - PROBLEM_DETECTED messages from content script → cache in chrome.storage
 *   - REQUEST_HINTS from popup → forward to backend with user's current code
 *   - SOLVE_COMPLETE from content script → post to /api/hints/solve-complete
 *   - Push notifications for review.due reminders
 */

const API_BASE = 'http://localhost/api';

// ─── Types ─────────────────────────────────────────────────────────────────

interface ProblemState {
  platform: string;
  slug: string;
  title: string;
  difficulty: string;
  tags: string[];
  url: string;
  userCode?: string;
  isAccepted?: boolean;
}

// ─── Message Router ────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.type) {
    case 'PROBLEM_DETECTED':
      handleProblemDetected(msg.payload as ProblemState).then(() =>
        sendResponse({ ok: true })
      );
      return true;

    case 'GET_CURRENT_PROBLEM':
      chrome.storage.session.get(['currentProblem'], (data) => {
        sendResponse({ problem: data.currentProblem || null });
      });
      return true;

    case 'REQUEST_HINTS':
      requestHints(msg.payload).then(sendResponse);
      return true;

    case 'SOLVE_COMPLETE':
      // Fired by content-script when LeetCode shows "Accepted"
      handleSolveComplete(msg.payload).then(sendResponse);
      return true;

    default:
      console.warn('[SW] Unknown message type:', msg.type);
  }
});

// ─── Handlers ──────────────────────────────────────────────────────────────

async function handleProblemDetected(info: ProblemState) {
  // Always update the stored problem with the latest code snapshot
  await chrome.storage.session.set({ currentProblem: info });
  console.log('[SW] Stored problem:', info.slug, '| code length:', info.userCode?.length ?? 0);

  // Badge the extension icon
  chrome.action.setBadgeText({ text: '!' });
  chrome.action.setBadgeBackgroundColor({ color: '#6378FF' });
  setTimeout(() => chrome.action.setBadgeText({ text: '' }), 3000);
}

async function requestHints(payload: {
  userId: string;
  problem: ProblemState;
  hintLevel: number;
}) {
  try {
    const token = await getAuthToken();

    // 1. Check fast-path Redis cache first
    const cacheRes = await fetch(
      `${API_BASE}/hints/cached/${payload.userId}/${payload.problem.slug}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    );
    if (cacheRes.ok) {
      const cached = await cacheRes.json();
      return { ok: true, hints: cached.hints, cached: true };
    }

    // 2. Grab latest code from stored problem state
    const stored = await new Promise<ProblemState | null>(resolve => {
      chrome.storage.session.get(['currentProblem'], (data) => {
        resolve((data.currentProblem as ProblemState) || null);
      });
    });
    const userCode = stored?.userCode || payload.problem?.userCode || '';

    // 3. Publish to Kafka via hint-service (including user's code)
    const res = await fetch(`${API_BASE}/hints/request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        user_id: payload.userId,
        problem_slug: payload.problem.slug,
        problem_title: payload.problem.title,
        difficulty: payload.problem.difficulty,
        tags: payload.problem.tags,
        hint_level: payload.hintLevel,
        user_code: userCode,   // ← user's current code for tailored hints
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const eventId = data.event_id;

    // 4. Poll for result
    for (let i = 0; i < 20; i++) {
      await new Promise(r => setTimeout(r, 500));
      const pollRes = await fetch(`${API_BASE}/hints/poll/${eventId}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      if (pollRes.ok) {
        const pollData = await pollRes.json();
        if (pollData.status === 'ready') {
          return { ok: true, hints: pollData.hints, eventId };
        }
      }
    }
    return { ok: true, hints: [], eventId, pending: true };
  } catch (e: any) {
    console.error('[SW] requestHints error:', e);
    return { ok: false, error: e.message };
  }
}

async function handleSolveComplete(payload: {
  problemSlug: string;
  difficulty: string;
  tags: string[];
  language: string;
  userCode?: string;
}) {
  try {
    const token = await getAuthToken();
    if (!token) return { ok: false, error: 'Not authenticated' };

    // Decode userId from JWT
    const jwtPayload = JSON.parse(atob(token.split('.')[1]));
    const userId = jwtPayload.sub;

    // POST to hint-service /solve-complete which publishes to solve.completed Kafka topic.
    // Progress-service and scheduler-service both consume that topic → update XP + review queue.
    const res = await fetch(`${API_BASE}/hints/solve-complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        user_id: userId,
        problem_slug: payload.problemSlug,
        difficulty: payload.difficulty,
        tags: payload.tags,
        language: payload.language,
        time_taken_seconds: 0,
        platform: 'leetcode',
        user_code: payload.userCode || '',
      }),
    });

    if (res.ok) {
      console.log('[SW] Solve recorded for:', payload.problemSlug);
      // Show a success notification
      chrome.notifications.create(`solve-${payload.problemSlug}`, {
        type: 'basic',
        iconUrl: '/icons/icon-128.png',
        title: 'DSA Buddy — Problem Solved! 🎉',
        message: `${payload.problemSlug.replace(/-/g, ' ')} marked as solved. XP awarded!`,
      });
    }
    return { ok: res.ok };
  } catch (e: any) {
    console.error('[SW] handleSolveComplete error:', e);
    return { ok: false, error: e.message };
  }
}

// ─── Auth helpers ──────────────────────────────────────────────────────────

async function getAuthToken(): Promise<string | null> {
  return new Promise(resolve => {
    chrome.storage.local.get(['accessToken'], (data: Record<string, unknown>) => {
      resolve((data.accessToken as string) || null);
    });
  });
}

// ─── Alarm: daily review reminder ─────────────────────────────────────────

chrome.alarms.create('daily-review-check', { periodInMinutes: 60 });
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== 'daily-review-check') return;
  const token = await getAuthToken();
  if (!token) return;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const userId = payload.sub;

    const res = await fetch(`${API_BASE}/schedule/due/${userId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const due = await res.json();
    if (!due || due.length === 0) return;

    chrome.notifications.create('review-reminder', {
      type: 'basic',
      iconUrl: '/icons/icon-128.png',
      title: 'DSA Buddy — Review Time!',
      message: `${due.length} problem${due.length > 1 ? 's' : ''} ready for spaced review today.`,
    });
  } catch (e) {
    console.error('[SW] Review check failed:', e);
  }
});

console.log('[DSA Buddy] Service worker initialized');
