const opt = (o: any) => o as Intl.DateTimeFormatOptions;
export const dt = (s?: string | null) => (s ? new Date(s).toLocaleString([], opt({ dateStyle: 'medium', timeStyle: 'short' })) : '—');
export const dd = (s?: string | null) =>
  s ? new Date(/^\d{4}-\d{2}-\d{2}$/.test(s) ? s + 'T00:00:00' : s).toLocaleDateString([], opt({ dateStyle: 'medium' })) : '—';
/** Scores may arrive as 0–1 or 0–100; normalise for display. */
export const pctOf = (v: any): number | null => (typeof v === 'number' ? Math.round(v <= 1 ? v * 100 : v) : null);
export const num = (v: any, d = 1) => (typeof v === 'number' ? String(Math.round(v * 10 ** d) / 10 ** d) : '—');
export const toIso = (local: string) => new Date(local).toISOString();
