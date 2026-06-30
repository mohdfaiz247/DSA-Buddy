export const API_BASE_URL = 'http://localhost'; // Port 80 via Nginx

export async function fetchWithAuth(endpoint: string, token: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API Error ${res.status}: ${errorBody}`);
  }
  return res.json();
}

export const progressApi = {
  getStats: (uid: string, token: string) => fetchWithAuth(`/api/progress/stats/${uid}`, token),
  getRecentSolves: (uid: string, token: string) => fetchWithAuth(`/api/progress/solves/${uid}`, token),
  syncLeetCodeSolves: (uid: string, token: string, slugs: string[]) => 
    fetchWithAuth(`/api/progress/sync`, token, {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, solved_slugs: slugs })
    }),
};

export const scheduleApi = {
  getQueue: (uid: string, token: string) => fetchWithAuth(`/api/schedule/queue/${uid}`, token),
  getDue: (uid: string, token: string) => fetchWithAuth(`/api/schedule/due/${uid}`, token),
};

export const analyticsApi = {
  getHeatmap: (uid: string, token: string) => fetchWithAuth(`/api/analytics/heatmap/${uid}`, token),
  getPatterns: (uid: string, token: string) => fetchWithAuth(`/api/analytics/patterns/${uid}`, token),
  getVelocity: (uid: string, token: string) => fetchWithAuth(`/api/analytics/velocity/${uid}`, token),
};

export const journalApi = {
  getEntries: (uid: string, token: string) => fetchWithAuth(`/api/problems/journal/${uid}`, token),
  createEntry: (uid: string, problemSlug: string, reflection: string, token: string) => 
    fetchWithAuth(`/api/problems/journal/`, token, {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, problem_slug: problemSlug, reflection })
    }),
};

export const problemApi = {
  /** Returns 5 recommended unsolved problems: 1 easy, 3 medium, 1 hard */
  getRecommendations: (uid: string, token: string) =>
    fetchWithAuth(`/api/problems/recommend/${uid}`, token),
  getReview: (uid: string, slug: string, token: string) =>
    fetchWithAuth(`/api/hints/review/${uid}/${slug}`, token),
};

export const solveApi = {
  /** Record a manual solve from the popup UI (fallback if content-script didn't fire) */
  recordSolve: (uid: string, token: string, payload: {
    problem_slug: string;
    difficulty: string;
    tags: string[];
    language?: string;
    time_taken_seconds?: number;
  }) =>
    fetchWithAuth(`/api/hints/solve-complete`, token, {
      method: 'POST',
      body: JSON.stringify({
        user_id: uid,
        ...payload,
        language: payload.language ?? 'unknown',
        time_taken_seconds: payload.time_taken_seconds ?? 0,
        platform: 'leetcode',
      }),
    }),
};

