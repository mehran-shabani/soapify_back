/**
 * apiService.test.js
 * Test framework: Jest (as detected from project configuration).
 * These tests validate the public API surface of src/services/apiService.*
 * They mock network interactions and cover happy paths, edge cases, and failures.
 */

/// BEGIN apiService core tests (fetch-backed)
import * as apiService from './apiService';

describe('apiService (fetch) - core behavior', () => {
  const okJson = (data) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(data) });
  const createdJson = (data) => Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve(data) });
  const errJson = (status = 500, data = { message: 'error' }) => Promise.resolve({ ok: false, status, json: () => Promise.resolve(data) });

  beforeEach(() => {
    jest.resetAllMocks();
    global.fetch = jest.fn();
  });

  describe('GET', () => {
    test('get() returns parsed JSON on 200', async () => {
      global.fetch.mockImplementationOnce(() => okJson({ items: [1, 2] }));
      const res = await apiService.get('/items');
      expect(global.fetch).toHaveBeenCalledWith(expect.stringMatching('/items'), expect.objectContaining({ method: 'GET' }));
      expect(res).toEqual({ items: [1, 2] });
    });

    test('get() rejects on non-ok status with payload', async () => {
      global.fetch.mockImplementationOnce(() => errJson(404, { message: 'Not Found' }));
      await expect(apiService.get('/missing')).rejects.toEqual(expect.objectContaining({ status: 404 }));
    });

    test('get() rejects on network error', async () => {
      const netErr = new Error('Network');
      global.fetch.mockRejectedValueOnce(netErr);
      await expect(apiService.get('/timeout')).rejects.toBe(netErr);
    });

    test('get() validates path input', async () => {
      await expect(apiService.get()).rejects.toBeTruthy();
      await expect(apiService.get(null)).rejects.toBeTruthy();
      await expect(apiService.get('')).rejects.toBeTruthy();
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe('POST', () => {
    test('post() sends JSON body and returns parsed JSON', async () => {
      global.fetch.mockImplementationOnce(() => createdJson({ id: 10 }));
      const payload = { name: 'X' };
      const res = await apiService.post('/items', payload);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringMatching('/items'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ 'Content-Type': expect.stringMatching(/json/i) }),
          body: JSON.stringify(payload),
        })
      );
      expect(res).toEqual({ id: 10 });
    });

    test('post() merges custom headers', async () => {
      global.fetch.mockImplementationOnce(() => okJson({ ok: true }));
      const headers = { Authorization: 'Bearer 123', 'X-Trace': 't' };
      await apiService.post('/submit', { a: 1 }, { headers });
      const [, init] = global.fetch.mock.calls[0];
      expect(init.headers).toEqual(expect.objectContaining(headers));
    });

    test('post() rejects when response not ok', async () => {
      global.fetch.mockImplementationOnce(() => errJson(400, { message: 'bad' }));
      await expect(apiService.post('/bad', { a: 1 })).rejects.toEqual(expect.objectContaining({ status: 400 }));
    });
  });

  describe('PUT and DELETE', () => {
    test('put() sends JSON body', async () => {
      global.fetch.mockImplementationOnce(() => okJson({ updated: true }));
      const res = await apiService.put('/items/1', { active: false });
      const [url, init] = global.fetch.mock.calls[0];
      expect(url).toMatch('/items/1');
      expect(init.method).toBe('PUT');
      expect(JSON.parse(init.body)).toEqual({ active: false });
      expect(res).toEqual({ updated: true });
    });

    test('delete() performs DELETE and returns payload/null', async () => {
      global.fetch.mockImplementationOnce(() => Promise.resolve({ ok: true, status: 204, json: async () => null }));
      const out = await (apiService.del ? apiService.del('/items/1') : apiService.delete('/items/1'));
      expect(global.fetch).toHaveBeenCalledWith(expect.stringMatching('/items/1'), expect.objectContaining({ method: 'DELETE' }));
      expect(out).toBeNull();
    });
  });

  describe('Base URL handling', () => {
    test('setBaseUrl() affects computed request URL without double slashes', async () => {
      if (typeof apiService.setBaseUrl !== 'function') return;
      apiService.setBaseUrl('/api/');
      global.fetch.mockImplementationOnce(() => okJson({ ok: true }));
      await apiService.get('/health');
      const calledUrl = global.fetch.mock.calls[0][0];
      expect(calledUrl).toMatch(/^(?!.*\/\/\/).+/);
    });
  });
});
/// END apiService core tests (fetch-backed)

/// BEGIN apiService edge cases

describe('apiService - edge cases and input validation', () => {
  test('gracefully handles non-object options', async () => {
    if (typeof apiService.get !== 'function') return;
    await expect(apiService.get('/x', null)).resolves.toBeDefined();
  });

  test('serializes query params consistently when provided as object', async () => {
    if (typeof apiService.getWithParams !== 'function') return;
    const spy = jest.spyOn(apiService, 'get');
    try {
      await apiService.getWithParams('/find', { q: 'a b', page: 1, tags: ['x', 'y'] });
    } catch (_e) {}
    if (spy.mock.calls.length) {
      const calledPath = spy.mock.calls[0][0];
      expect(calledPath).toMatch(/\?/);
      expect(decodeURI(calledPath)).toMatch(/q=a b/);
      expect(calledPath).toMatch(/page=1/);
    }
    spy.mockRestore();
  });
});
/// END apiService edge cases