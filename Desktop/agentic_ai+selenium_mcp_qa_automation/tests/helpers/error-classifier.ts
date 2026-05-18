/**
 * Root-cause categories for test failures.
 * These categories appear in the Playwright HTML report annotations and in
 * CI failure summaries so that engineers can triage quickly without reading
 * full stack traces.
 */
export type ErrorCategory =
  | 'ELEMENT_NOT_FOUND'
  | 'ELEMENT_NOT_VISIBLE'
  | 'TIMEOUT'
  | 'ASSERTION_ERROR'
  | 'NAVIGATION_ERROR'
  | 'UNKNOWN';

const CATEGORY_ICONS: Record<ErrorCategory, string> = {
  ELEMENT_NOT_FOUND: '🔍',
  ELEMENT_NOT_VISIBLE: '👁',
  TIMEOUT: '⏱',
  ASSERTION_ERROR: '❌',
  NAVIGATION_ERROR: '🌐',
  UNKNOWN: '❓',
};

/** Inspects the error message and returns the most likely root cause category. */
export function classifyError(err: unknown): ErrorCategory {
  const msg = (err instanceof Error ? err.message : String(err)).toLowerCase();

  if (
    msg.includes('element_not_found') ||
    msg.includes('exhausted all strategies') ||
    msg.includes('resolved to 0 elements') ||
    msg.includes('no element') ||
    msg.includes('strict mode violation')
  )
    return 'ELEMENT_NOT_FOUND';

  if (
    msg.includes('not visible') ||
    msg.includes('resolved to hidden') ||
    msg.includes('element_not_visible')
  )
    return 'ELEMENT_NOT_VISIBLE';

  if (
    msg.includes('timeout') ||
    msg.includes('exceeded') ||
    msg.includes('waiting for') ||
    msg.includes('timed out')
  )
    return 'TIMEOUT';

  if (
    msg.includes('tohaveurl') ||
    msg.includes('tohavetext') ||
    msg.includes('tocontaintext') ||
    msg.includes('toequal') ||
    msg.includes('tobetruthy') ||
    (msg.includes('expect') && msg.includes('received'))
  )
    return 'ASSERTION_ERROR';

  if (
    msg.includes('net::err') ||
    msg.includes('connection refused') ||
    msg.includes('navigation failed')
  )
    return 'NAVIGATION_ERROR';

  return 'UNKNOWN';
}

/**
 * Formats a failure into a one-line human-readable summary suitable for
 * CI logs and Slack notifications.
 *
 * Example output:
 *   ❌ [ASSERTION_ERROR] TC-CO04: order total is $104.98
 *     Expected string containing "$104.98" but received "$99.99"
 */
export function formatFailure(testTitle: string, err: unknown): string {
  const category = classifyError(err);
  const icon = CATEGORY_ICONS[category];
  const firstLine = (err instanceof Error ? err.message : String(err)).split('\n')[0];
  return `${icon} [${category}] ${testTitle}\n  ${firstLine}`;
}
