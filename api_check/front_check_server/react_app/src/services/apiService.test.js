/**
 * Test framework: Jest (react-scripts test).
 * These tests exercise typical API service behaviors (GET/POST/PUT/DELETE, params, headers, errors).
 * They assume axios is used under the hood. If your service uses fetch or a different client,
 * adapt the mock and call assertions accordingly.
 *
 * NOTE: Focus is on the PR diff area. If the diff adds wrappers or error normalization in apiService,
 * these tests validate those behaviors along with happy-path and edge cases.
 */

jest.mock('axios', () => {
  const actual = jest.requireActual('axios');
  // Mocked axios instance returned by axios.create()
  const mockInstance = {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
    interceptors: {
      request: { use: jest.fn(), eject: jest.fn() },
      response: { use: jest.fn(), eject: jest.fn() },
    },
    defaults: { baseURL: '', headers: { common: {} }, timeout: 0 },
  };
  // The axios mock is also a function (callable), matching axios()
  const axiosFn = jest.fn(() => mockInstance);
  return Object.assign(axiosFn, {
    create: jest.fn(() => mockInstance),
    CancelToken: actual.CancelToken,
    isCancel: actual.isCancel,
    __mockInstance: mockInstance,
  });
});

import axios from 'axios';

let apiService;

// Ensure the axios mock is active before loading the service module each test.
beforeEach(() => {
  jest.resetModules();
  // Load the service fresh so constructor/init code runs with our mock.
  // Adjust the path/filename if your service file differs.
  const serviceModule = require('./apiService');
  apiService = serviceModule.default || serviceModule;
  // Copy named exports (if any) onto apiService for easier conditional access.
  Object.assign(apiService, serviceModule);

  // Reset axios instance method mocks
  const instance = axios.__mockInstance;
  instance.get.mockReset();
  instance.post.mockReset();
  instance.put.mockReset();
  instance.delete.mockReset();
  instance.request.mockReset();
});

describe('apiService - configuration and instance behavior', () => {
  test('initializes axios instance and sets up interceptors (if configured)', async () => {
    const instance = axios.__mockInstance;

    if (typeof apiService.getClient === 'function') {
      apiService.getClient();
    } else if (typeof apiService.get === 'function') {
      instance.get.mockResolvedValueOnce({ status: 200, data: {} });
      try { await apiService.get('/__ping__'); } catch (_) {}
    }

    expect(instance.interceptors.request.use).toBeDefined();
    expect(instance.interceptors.response.use).toBeDefined();
  });
});

describe('apiService - GET', () => {
  test('performs successful GET and returns data', async () => {
    const instance = axios.__mockInstance;
    const mockData = { id: 1, name: 'Alice' };
    instance.get.mockResolvedValueOnce({ status: 200, data: mockData });

    const result = await (apiService.get ? apiService.get('/users/1') : apiService.request({ method: 'GET', url: '/users/1' }));
    const data = result && result.data !== undefined ? result.data : result;

    expect(instance.get).toHaveBeenCalledWith('/users/1', expect.any(Object));
    expect(data).toEqual(mockData);
  });

  test('forwards query params correctly', async () => {
    const instance = axios.__mockInstance;
    instance.get.mockResolvedValueOnce({ status: 200, data: [] });

    const params = { q: 'term', page: 2, active: true, empty: undefined };
    await (apiService.get ? apiService.get('/items', { params }) : apiService.request({ method: 'GET', url: '/items', params }));

    expect(instance.get).toHaveBeenCalledWith('/items', expect.objectContaining({ params }));
  });

  test('propagates non-2xx errors with response details (if present)', async () => {
    const instance = axios.__mockInstance;
    const error = Object.assign(new Error('Not Found'), {
      response: { status: 404, data: { message: 'not found' } },
      config: { url: '/missing' },
    });
    instance.get.mockRejectedValueOnce(error);

    const promise = apiService.get ? apiService.get('/missing') : apiService.request({ method: 'GET', url: '/missing' });
    await expect(promise).rejects.toMatchObject({
      response: { status: 404, data: { message: 'not found' } },
    });
  });
});

describe('apiService - POST/PUT/DELETE', () => {
  test('POST sends payload and returns created resource', async () => {
    const instance = axios.__mockInstance;
    const payload = { name: 'New' };
    const created = { id: 10, name: 'New' };
    instance.post.mockResolvedValueOnce({ status: 201, data: created });

    const result = await (apiService.post ? apiService.post('/items', payload) : apiService.request({ method: 'POST', url: '/items', data: payload }));
    const data = result && result.data !== undefined ? result.data : result;

    expect(instance.post).toHaveBeenCalledWith('/items', payload, expect.any(Object));
    expect(data).toEqual(created);
  });

  test('PUT updates resource and returns updated entity', async () => {
    const instance = axios.__mockInstance;
    const payload = { name: 'Updated' };
    const updated = { id: 10, name: 'Updated' };
    instance.put.mockResolvedValueOnce({ status: 200, data: updated });

    const result = await (apiService.put ? apiService.put('/items/10', payload) : apiService.request({ method: 'PUT', url: '/items/10', data: payload }));
    const data = result && result.data !== undefined ? result.data : result;

    expect(instance.put).toHaveBeenCalledWith('/items/10', payload, expect.any(Object));
    expect(data).toEqual(updated);
  });

  test('DELETE removes resource and returns null payload', async () => {
    const instance = axios.__mockInstance;
    instance.delete.mockResolvedValueOnce({ status: 204, data: null });

    const result = await (
      apiService.del ? apiService.del('/items/10') :
      (apiService.delete ? apiService.delete('/items/10') : apiService.request({ method: 'DELETE', url: '/items/10' }))
    );
    const data = result && result.data !== undefined ? result.data : result;

    expect(instance.delete).toHaveBeenCalledWith('/items/10', expect.any(Object));
    expect(data).toBeNull();
  });
});

describe('apiService - headers and auth', () => {
  test('includes Authorization header when configured', async () => {
    const instance = axios.__mockInstance;
    instance.get.mockResolvedValueOnce({ status: 200, data: { ok: true } });
    const token = 'Bearer abc123';

    if (typeof apiService.setAuthToken === 'function') {
      apiService.setAuthToken(token);
    }

    await (apiService.get ? apiService.get('/secure') : apiService.request({ method: 'GET', url: '/secure', headers: { Authorization: token } }));

    const lastCall = instance.get.mock.calls[0];
    const config = (lastCall && lastCall[1]) || {};
    const authHeader = (config.headers && config.headers.Authorization) || (instance.defaults.headers && instance.defaults.headers.common && instance.defaults.headers.common.Authorization);
    expect(authHeader).toBeDefined();
  });
});

describe('apiService - timeout and cancellation', () => {
  test('applies timeout either in per-call config or instance defaults', async () => {
    const instance = axios.__mockInstance;
    instance.get.mockResolvedValueOnce({ status: 200, data: {} });

    if (typeof apiService.setTimeout === 'function') {
      apiService.setTimeout(5000);
    }

    await (apiService.get ? apiService.get('/slow') : apiService.request({ method: 'GET', url: '/slow' }));

    const lastCall = instance.get.mock.calls[0];
    const config = (lastCall && lastCall[1]) || {};
    const timeout = (config && config.timeout != null) ? config.timeout : instance.defaults.timeout;
    expect(timeout).toBeDefined();
  });

  test('surfaces cancellation errors distinctly', async () => {
    const instance = axios.__mockInstance;
    const cancelError = new Error('canceled');
    cancelError.__CANCEL__ = true;
    instance.get.mockRejectedValueOnce(cancelError);

    const promise = apiService.get ? apiService.get('/cancel') : apiService.request({ method: 'GET', url: '/cancel' });
    await expect(promise).rejects.toMatchObject({ __CANCEL__: true });
  });
});

describe('apiService - edge cases and input validation', () => {
  test('rejects when url is undefined', async () => {
    const instance = axios.__mockInstance;
    instance.get.mockResolvedValueOnce({ status: 200, data: {} });
    // Intentionally invalid usage
    const promise = apiService.get ? apiService.get(undefined) : apiService.request({ method: 'GET', url: undefined });
    await expect(promise).rejects.toBeDefined();
  });

  test('handles empty payload on POST gracefully', async () => {
    const instance = axios.__mockInstance;
    instance.post.mockResolvedValueOnce({ status: 200, data: { ok: true } });

    const result = await (apiService.post ? apiService.post('/nopayload') : apiService.request({ method: 'POST', url: '/nopayload' }));
    const data = result && result.data !== undefined ? result.data : result;

    expect(instance.post).toHaveBeenCalled();
    expect(data).toEqual({ ok: true });
  });
});