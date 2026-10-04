import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, ApiError, asList, setTokens } from './client';

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));

beforeEach(() => { setTokens(null); vi.restoreAllMocks(); });

describe('api client', () => {
  it('unwraps the success envelope', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(200, { success: true, data: { a: 1 } })));
    expect(await api('/api/x')).toEqual({ a: 1 });
  });
  it('throws typed errors from the failure envelope', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(403, { success: false, error: { code: 'forbidden', message: 'Nope' } })));
    await expect(api('/api/x')).rejects.toMatchObject({ status: 403, code: 'forbidden', message: 'Nope' });
  });
  it('refreshes once on 401 and retries', async () => {
    setTokens({ access_token: 'old', refresh_token: 'r1' });
    const f = vi.fn()
      .mockImplementationOnce(() => json(401, { success: false, error: { code: 'expired', message: 'x' } }))
      .mockImplementationOnce(() => json(200, { success: true, data: { student: {}, tokens: { access_token: 'new', refresh_token: 'r2' } } }))
      .mockImplementationOnce(() => json(200, { success: true, data: 'ok' }));
    vi.stubGlobal('fetch', f);
    expect(await api('/api/x')).toBe('ok');
    expect(f).toHaveBeenCalledTimes(3);
  });
  it('maps network failure to ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('fail'))));
    await expect(api('/api/x')).rejects.toBeInstanceOf(ApiError);
  });
});

describe('asList', () => {
  it('finds arrays in unknown shapes', () => {
    expect(asList([1])).toEqual([1]);
    expect(asList({ items: [2] })).toEqual([2]);
    expect(asList({ foo: [3] })).toEqual([3]);
    expect(asList(null)).toEqual([]);
  });
});
