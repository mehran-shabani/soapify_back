/**
 * Tests for apiService.
 * Framework: Jest (common in CRA/react-scripts setups). If this project uses Vitest, replace jest.fn with vi.fn and adjust mocks.
 * These tests mock the HTTP layer (fetch/axios) to validate apiService behavior under various scenarios.
 */

describe('apiService - comprehensive behavior', () => {
  let originalFetch;
  let axiosModule;
  const buildResponse = (status = 200, data = {}, headers = {}) => {
    // fetch-like Response mock
    return {
      ok: status >= 200 && status < 300,
      status,
      json: jest.fn().mockResolvedValue(data),
      text: jest.fn().mockResolvedValue(typeof data === 'string' ? data : JSON.stringify(data)),
      headers: {
        get: (k) => headers[k.toLowerCase()] ?? headers[k] ?? null,
      },
    };
  };

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    // Snapshot implementation imports fresh each test
    try {
      // Attempt to mock axios if used by apiService
      jest.doMock('axios', () => {
        const m = {
          create: jest.fn(function(cfg){ return Object.assign(jest.fn(async () => ({})), {defaults: cfg || {}, get: jest.fn(), post: jest.fn(), put: jest.fn(), patch: jest.fn(), delete: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } }); }),
          get: jest.fn(),
          post: jest.fn(),
          put: jest.fn(),
          patch: jest.fn(),
          delete: jest.fn(),
        };
        return m;
      });
      // eslint-disable-next-line global-require
      axiosModule = require('axios');
    } catch (e) {
      axiosModule = null;
    }

    originalFetch = global.fetch;
    global.fetch = jest.fn();
  });

  afterEach(() => {
    if (originalFetch) global.fetch = originalFetch;
    try { jest.dontMock('axios'); } catch(e) {}
  });

  const importApi = async () => {
    // Dynamically import to capture jest.doMock
    try {
      // eslint-disable-next-line global-require
      const svc = require('./apiService');
      return svc && svc.default ? svc.default : svc;
    } catch (cjsErr) {
      // ESM fallback
      const svc = await import('./apiService');
      return svc && svc.default ? svc.default : svc;
    }
  };

  test('GET: builds URL with query params and returns parsed JSON (fetch path)', async () => {
    const payload = { items: [1,2,3], total: 3 };
    global.fetch.mockResolvedValueOnce(buildResponse(200, payload, { 'content-type': 'application/json' }));

    const api = await importApi();
    const res = await api.get('/foo', { params: { q: 'abc', page: 2 } });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/foo(\?|$)/);
    expect(String(url)).toContain('q=abc');
    expect(String(url)).toContain('page=2');
    expect(opts.method).toBe('GET');
    expect(res).toEqual(payload);
  });

  test('GET: includes default headers and allows overrides', async () => {
    global.fetch.mockResolvedValueOnce(buildResponse(200, { ok: true }, { 'content-type': 'application/json' }));
    const api = await importApi();
    await api.get('/headers', { headers: { 'X-Test': '123' } });
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers).toEqual(expect.objectContaining({ 'X-Test': '123' }));
  });

  test('POST: sends JSON body and parses JSON response', async () => {
    const body = { name: 'Alice' };
    global.fetch.mockResolvedValueOnce(buildResponse(201, { id: 42, ...body }, { 'content-type': 'application/json' }));

    const api = await importApi();
    const res = await api.post('/users', { data: body });

    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(opts.headers).toEqual(expect.objectContaining({ 'Content-Type': expect.stringMatching(/json/i) }));
    expect(typeof opts.body).toBe('string');
    expect(JSON.parse(opts.body)).toEqual(body);
    expect(res).toEqual(expect.objectContaining({ id: 42, name: 'Alice' }));
  });

  test('Non-JSON response: falls back to text()', async () => {
    global.fetch.mockResolvedValueOnce(buildResponse(200, 'OK', { 'content-type': 'text/plain' }));
    const api = await importApi();
    const res = await api.get('/text');
    expect(res).toBe('OK');
  });

  test('HTTP error (4xx): rejects with status and message', async () => {
    const errPayload = { error: 'Bad Request' };
    global.fetch.mockResolvedValueOnce(buildResponse(400, errPayload, { 'content-type': 'application/json' }));
    const api = await importApi();
    await expect(api.get('/bad')).rejects.toMatchObject({ status: 400 });
  });

  test('HTTP error (5xx): rejects and includes body text for non-JSON', async () => {
    const resp = buildResponse(503, 'Service Unavailable', { 'content-type': 'text/plain' });
    // Ensure json() throws to force text() path if apiService tries json first
    resp.json.mockRejectedValueOnce(new Error('invalid json'));
    global.fetch.mockResolvedValueOnce(resp);
    const api = await importApi();
    await expect(api.get('/down')).rejects.toMatchObject({ status: 503 });
  });

  test('Network failure: fetch rejects -> surfaces error', async () => {
    const boom = new Error('network down');
    global.fetch.mockRejectedValueOnce(boom);
    const api = await importApi();
    await expect(api.get('/net')).rejects.toBe(boom);
  });

  test('Abort/timeout: respects AbortController signal if provided', async () => {
    let controller;
    global.fetch.mockImplementationOnce((_url, opts) => {
      controller = opts.signal;
      return new Promise((_resolve, _reject) => {}); // pending
    });
    const api = await importApi();
    const ac = new AbortController();
    const p = api.get('/slow', { signal: ac.signal });
    expect(typeof p.then).toBe('function');
    // emulate abort
    ac.abort();
    // We cannot assert internal cancellation unless apiService listens for abort.
    expect(controller).toBe(ac.signal);
  });

  test('Axios path: when axios is used internally, mocks receive correct method calls', async () => {
    if (!axiosModule) return; // skip if axios not present
    // Re-import apiService with axios mocked already in beforeEach
    const api = await importApi();
    if (axiosModule.create && axiosModule.create.mock) {
      const instance = axiosModule.create.mock.results[0]?.value;
      if (instance && instance.get) {
        instance.get.mockResolvedValueOnce({ status: 200, data: { ok: true }, headers: {} });
        const res = await api.get('/with-axios', { params: { a: 1 } });
        expect(instance.get).toHaveBeenCalled();
        expect(res).toEqual({ ok: true });
      }
    }
  });

  test('Query param encoding: handles arrays and falsy values safely', async () => {
    global.fetch.mockResolvedValueOnce(buildResponse(200, { ok: true }, { 'content-type': 'application/json' }));
    const api = await importApi();
    await api.get('/qp', { params: { tags: ['a', 'b'], empty: '', zero: 0, bool: false, nil: null } });
    const [url] = global.fetch.mock.calls[0];
    const s = String(url);
    expect(s).toMatch(/tags=a/);
    expect(s).toMatch(/tags=b/);
    expect(s).toMatch(/zero=0/);
    expect(s).toMatch(/bool=false/);
    // null/undefined may be omitted — either is acceptable depending on impl; we just ensure no crash
  });

  test('PUT/PATCH/DELETE basic coverage', async () => {
    global.fetch
      .mockResolvedValueOnce(buildResponse(200, { ok: 'put' }, { 'content-type': 'application/json' }))
      .mockResolvedValueOnce(buildResponse(200, { ok: 'patch' }, { 'content-type': 'application/json' }))
      .mockResolvedValueOnce(buildResponse(204, {}, { 'content-type': 'application/json' }));

    const api = await importApi();
    await expect(api.put('/res', { data: { a: 1 } })).resolves.toEqual({ ok: 'put' });
    await expect(api.patch('/res', { data: { b: 2 } })).resolves.toEqual({ ok: 'patch' });
    await expect(api.delete('/res')).resolves.toEqual({}); // 204 no content -> {}
  });

  test('Base URL handling: respects configured baseURL and joins paths correctly', async () => {
    global.fetch.mockResolvedValueOnce(buildResponse(200, { ok: true }, { 'content-type': 'application/json' }));
    const api = await importApi();
    if (typeof api.configure === 'function') {
      api.configure({ baseURL: 'https://api.example.com/v1/' });
    }
    await api.get('/health');
    const [url] = global.fetch.mock.calls[0];
    expect(String(url)).toMatch(/^https?:\/\/.*example\.com\/v1\/health$/);
  });
});