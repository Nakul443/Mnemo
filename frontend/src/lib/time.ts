/**
 * Formats a millisecond timestamp into a human-readable relative duration string.
 * Pure function accepting explicit `now` parameter for testability.
 */
export function relativeTime(ts: number, now: number): string {
  const diffSec = Math.max(0, Math.floor((now - ts) / 1000));
  if (diffSec < 60) {
    return "just now";
  }
  const minutes = Math.floor(diffSec / 60);
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} h ago`;
  }
  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days} days ago`;
  }
  const weeks = Math.floor(days / 7);
  return `${weeks} weeks ago`;
}
