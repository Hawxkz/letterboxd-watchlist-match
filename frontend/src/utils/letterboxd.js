/**
 * Extracts a clean Letterboxd username from a raw username, @handle, or full profile/watchlist URL.
 * Examples:
 * - 'alice' -> 'alice'
 * - '@alice' -> 'alice'
 * - 'https://letterboxd.com/alice/' -> 'alice'
 * - 'https://letterboxd.com/alice/watchlist/' -> 'alice'
 * - 'letterboxd.com/alice/films/' -> 'alice'
 */
export function extractLetterboxdUsername(input) {
  if (!input) return '';
  let str = input.trim();

  if (str.toLowerCase().includes('letterboxd.com')) {
    try {
      const normalized = str.startsWith('http://') || str.startsWith('https://')
        ? str
        : `https://${str}`;
      const url = new URL(normalized);
      const parts = url.pathname.split('/').filter(Boolean);
      if (parts.length > 0) {
        return parts[0].replace(/^@+/, '').trim();
      }
    } catch {
      const match = str.match(/letterboxd\.com\/([a-zA-Z0-9_-]+)/i);
      if (match && match[1]) {
        return match[1].replace(/^@+/, '').trim();
      }
    }
  }

  return str.replace(/^@+/, '').replace(/\/+$/, '').trim();
}
