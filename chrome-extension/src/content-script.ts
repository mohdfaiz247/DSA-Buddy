/**
 * DSA Buddy Content Script
 * Injected into LeetCode, Codeforces, HackerRank, AtCoder pages.
 * Detects active problem metadata, current code, and submission results.
 */

interface ProblemInfo {
  platform: string;
  slug: string;
  title: string;
  difficulty: string;
  tags: string[];
  url: string;
}

interface ProblemState extends ProblemInfo {
  userCode?: string;
  isAccepted?: boolean;
}

// ─── Platform Detectors ────────────────────────────────────────────────────

function detectLeetCode(): ProblemInfo | null {
  const url = window.location.href;
  const match = url.match(/leetcode\.com\/problems\/([\w-]+)/);
  if (!match) return null;

  const slug = match[1];
  const title = document.querySelector<HTMLElement>(
    '[data-cy="question-title"], .mr-2.text-label-1, [class*="title__"]'
  )?.innerText?.trim() || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  const diffEl = document.querySelector<HTMLElement>(
    '[diff],.difficulty-label,.text-olive,.text-yellow,.text-pink,[class*="difficulty"]'
  );
  const rawDiff = diffEl?.innerText?.toLowerCase() || '';
  const difficulty = rawDiff.includes('easy') ? 'easy'
    : rawDiff.includes('hard') ? 'hard'
    : 'medium';

  const tagEls = document.querySelectorAll<HTMLElement>('.topic-tag__1jni, a[href*="/tag/"]');
  const tags = Array.from(tagEls).map(el => el.innerText.trim().toLowerCase()).filter(Boolean);

  return { platform: 'leetcode', slug, title, difficulty, tags, url };
}

function detectCodeforces(): ProblemInfo | null {
  const url = window.location.href;
  const match = url.match(/codeforces\.com\/(?:contest|problemset).*?\/problem\/(\w+)\/(\w+)/);
  if (!match) return null;

  const slug = `cf-${match[1]}-${match[2]}`;
  const title = document.querySelector<HTMLElement>('.problem-statement .title')?.innerText?.trim() || slug;
  return { platform: 'codeforces', slug, title, difficulty: 'medium', tags: [], url };
}

function detectAtCoder(): ProblemInfo | null {
  const url = window.location.href;
  const match = url.match(/atcoder\.jp\/contests\/([\w-]+)\/tasks\/([\w-]+)/);
  if (!match) return null;

  const slug = `atcoder-${match[2]}`;
  const title = document.querySelector<HTMLElement>('#task-statement .h2, span.h2')?.innerText?.trim() || slug;
  return { platform: 'atcoder', slug, title, difficulty: 'medium', tags: [], url };
}

function detectHackerRank(): ProblemInfo | null {
  const url = window.location.href;
  const match = url.match(/hackerrank\.com\/challenges\/([\w-]+)/);
  if (!match) return null;

  const slug = `hr-${match[1]}`;
  const title = document.querySelector<HTMLElement>('.challenge-page-label-title, h1')?.innerText?.trim() || slug;
  return { platform: 'hackerrank', slug, title, difficulty: 'medium', tags: [], url };
}

// ─── Code Scraper ─────────────────────────────────────────────────────────

function scrapeUserCode(): string {
  // LeetCode Monaco editor — lines are stored in .view-lines
  const monacoLines = document.querySelectorAll<HTMLElement>('.view-lines .view-line');
  if (monacoLines.length > 0) {
    return Array.from(monacoLines).map(l => l.innerText).join('\n').trim();
  }

  // Fallback: CodeMirror (older LeetCode / Codeforces)
  const cm = document.querySelector<HTMLElement>('.CodeMirror-code');
  if (cm) return cm.innerText.trim();

  // Fallback: textareas (HackerRank, AtCoder)
  const textarea = document.querySelector<HTMLTextAreaElement>('textarea.editor, #editor textarea');
  if (textarea) return textarea.value.trim();

  return '';
}

// ─── Accepted Submission Detector ────────────────────────────────────────

function detectAcceptedSubmission(): boolean {
  // LeetCode shows "Accepted" in the result panel
  const resultText = document.querySelector<HTMLElement>(
    '[data-e2e-locator="submission-result"], [class*="accepted"], [class*="Accepted"]'
  )?.innerText?.toLowerCase() || '';
  return resultText.includes('accepted');
}

// ─── Main Detector ────────────────────────────────────────────────────────

function detectProblem(): ProblemInfo | null {
  const host = window.location.hostname;
  if (host.includes('leetcode')) return detectLeetCode();
  if (host.includes('codeforces')) return detectCodeforces();
  if (host.includes('atcoder')) return detectAtCoder();
  if (host.includes('hackerrank')) return detectHackerRank();
  return null;
}

// ─── Send to Service Worker ───────────────────────────────────────────────

function sendProblemInfo(info: ProblemState) {
  chrome.runtime.sendMessage({
    type: 'PROBLEM_DETECTED',
    payload: info,
  });
}

// ─── DOM Observation ──────────────────────────────────────────────────────

let lastSlug = '';
let lastAccepted = false;

function tryDetect() {
  const info = detectProblem();
  if (!info) return;

  const userCode = scrapeUserCode();
  const isAccepted = detectAcceptedSubmission();

  // Send on new problem or first accepted detection
  if (info.slug !== lastSlug || (isAccepted && !lastAccepted)) {
    if (info.slug !== lastSlug) lastSlug = info.slug;
    if (isAccepted) lastAccepted = true;

    const state: ProblemState = { ...info, userCode, isAccepted };
    sendProblemInfo(state);
    console.debug('[DSA Buddy] Detected:', state);

    // If newly accepted — fire SOLVE_COMPLETE separately so service worker logs the solve
    if (isAccepted) {
      chrome.runtime.sendMessage({
        type: 'SOLVE_COMPLETE',
        payload: {
          problemSlug: info.slug,
          difficulty: info.difficulty,
          tags: info.tags,
          language: detectLanguage(),
          userCode: userCode, // Send code for post-solve AI review
        },
      });
      console.log('[DSA Buddy] Solve complete fired for:', info.slug);
    }
  }
}

function detectLanguage(): string {
  // LeetCode shows the language in a dropdown or button
  const langEl = document.querySelector<HTMLElement>(
    '[data-cy="lang-select"] button, [id*="lang-"] button, [class*="lang"] button'
  );
  const lang = langEl?.innerText?.trim().toLowerCase() || 'unknown';
  if (lang.includes('python')) return 'python';
  if (lang.includes('java') && !lang.includes('script')) return 'java';
  if (lang.includes('c++') || lang.includes('cpp')) return 'cpp';
  if (lang.includes('javascript') || lang.includes('js')) return 'javascript';
  if (lang.includes('typescript') || lang.includes('ts')) return 'typescript';
  if (lang.includes('go')) return 'go';
  if (lang.includes('rust')) return 'rust';
  return lang || 'unknown';
}

// Run immediately
tryDetect();

// Re-run on route changes (SPA navigation)
const observer = new MutationObserver(() => tryDetect());
observer.observe(document.body, { childList: true, subtree: true });

// Also poll every 2s to pick up accepted result and code changes
setInterval(tryDetect, 2000);
