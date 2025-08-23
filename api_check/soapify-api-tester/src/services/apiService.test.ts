import axios, { AxiosRequestConfig } from 'axios';
import ApiService from './apiService';
import { ApiEndpoint, TestConfig } from '../types';
import * as helpers from '../utils/helpers';

// NOTE ON TEST FRAMEWORK:
// These tests are written for Jest (commonly used in TS repos). If your project uses Vitest,
// change jest.fn/jest.spyOn to vi.fn/vi.spyOn and update the mock factory accordingly.

jest.mock('axios', () => {
  const actual = jest.requireActual('axios');
  const mockAxios = jest.fn();
  // Attach helpers used in code under test
  (mockAxios as any).isAxiosError = (err: any) => !!(err && (err.isAxiosError || err.code || err.response));
  // Pass through AxiosError class if needed by tests
  (mockAxios as any).AxiosError = (actual as any).AxiosError || class extends Error {};
  return mockAxios;
});

jest.mock('../utils/helpers', () => ({
  generateId: jest.fn(() => 'test-id-123'),
  calculateResponseAccuracy: jest.fn(() => 88.5),
}));

const mockedAxios = axios as unknown as jest.Mock;

describe('ApiService', () => {
  const baseConfig: TestConfig = {
    baseUrl: 'https://api.example.com',
    timeout: 5000,
    customHeaders: { 'X-Env': 'test', 'Content-Type': 'application/custom' }, // overridden by default JSON then endpoint.headers
    retries: 2,
    concurrency: 2,
    authToken: 'abc123'
  };

  const getEndpoint = (overrides: Partial<ApiEndpoint> = {}): ApiEndpoint => ({
    name: 'Get Users',
    method: 'GET',
    path: '/users',
    headers: {},
    query_params: undefined,
    payload: undefined,
    auth_required: false,
    expected_response: undefined,
    ...overrides,
  });

  const setNowSequence = (values: number[]) => {
    let idx = 0;
    jest.spyOn(Date, 'now').mockImplementation(() => values[Math.min(idx++, values.length - 1)]);
  };

  beforeEach(() => {
    jest.useFakeTimers({ legacyFakeTimers: false });
    jest.spyOn(global, 'setTimeout');
    jest.clearAllMocks();
    // Default helper mocks
    (helpers.generateId as jest.Mock).mockReturnValue('test-id-123');
    (helpers.calculateResponseAccuracy as jest.Mock).mockReturnValue(88.5);
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
    jest.clearAllMocks();
  });

  test('testEndpoint success (GET) computes times, sizes, status and accuracy (when expected_response provided)', async () => {
    const svc = new ApiService(baseConfig);
    const endpoint = getEndpoint({ expected_response: { ok: true }, query_params: { page: 2 } });

    // Timing: start=1000, pre=1100, end=1300 => request=100, response=200, total=300
    setNowSequence([1000, 1100, 1300]);

    mockedAxios.mockResolvedValueOnce({
      status: 200,
      data: { ok: true, users: [] },
      headers: { 'x-res': '1' }
    });

    const result = await svc.testEndpoint(endpoint);

    // axios called once with built config
    expect(mockedAxios).toHaveBeenCalledTimes(1);
    const passedConfig: AxiosRequestConfig = mockedAxios.mock.calls[0][0];

    // Request config assertions
    expect(passedConfig.method).toBe('GET');
    expect(passedConfig.url).toBe('https://api.example.com/users');
    expect(passedConfig.timeout).toBe(5000);
    expect(passedConfig.params).toEqual({ page: 2 });
    expect(passedConfig.headers).toMatchObject({
      'Content-Type': 'application/json',
      'X-Env': 'test',
    });
    // No Authorization when auth_required: false
    expect((passedConfig.headers as any)['Authorization']).toBeUndefined();
    // AbortSignal present
    expect((passedConfig as any).signal).toBeInstanceOf(AbortSignal);

    // Result assertions
    expect(result.id).toBe('test-id-123');
    expect(result.status).toBe('success');
    expect(result.statusCode).toBe(200);
    expect(result.response).toEqual({ ok: true, users: [] });
    expect(result.actualResponse).toEqual({ ok: true, users: [] });

    // Timing
    expect(result.requestTime).toBe(100);
    expect(result.responseTime).toBe(200);
    expect(result.totalTime).toBe(300);

    // Sizes
    // headers size (stringified) + url + params size
    const expectedReqSize =
      JSON.stringify(passedConfig.headers).length +
      (passedConfig.url || '').length +
      JSON.stringify(passedConfig.params).length;
    expect(result.requestSize).toBe(expectedReqSize);

    const expectedRespSize =
      JSON.stringify({ 'x-res': '1' }).length +
      JSON.stringify({ ok: true, users: [] }).length;
    expect(result.responseSize).toBe(expectedRespSize);

    // Accuracy calculated since expected_response provided
    expect(helpers.calculateResponseAccuracy).toHaveBeenCalledWith(
      { ok: true },
      { ok: true, users: [] }
    );
    expect(result.accuracyPercentage).toBe(88.5);
  });

  test('testEndpoint attaches Authorization when auth_required and token present; endpoint headers override custom headers', async () => {
    const svc = new ApiService(baseConfig);
    const endpoint = getEndpoint({
      method: 'POST',
      path: '/items',
      payload: { a: 1 },
      auth_required: true,
      headers: { 'X-Env': 'endpoint', 'Content-Type': 'application/override' },
    });

    setNowSequence([1000, 1050, 1200]);
    mockedAxios.mockResolvedValueOnce({ status: 201, data: { id: 1 }, headers: {} });

    const result = await svc.testEndpoint(endpoint);
    const cfg: AxiosRequestConfig = mockedAxios.mock.calls[0][0];

    // endpoint.headers should override custom headers
    expect(cfg.headers).toMatchObject({
      'Content-Type': 'application/override',
      'X-Env': 'endpoint',
      'Authorization': 'Bearer abc123',
    });
    // POST carries payload in data
    expect(cfg.data).toEqual({ a: 1 });

    expect(result.status).toBe('success');
    expect(result.statusCode).toBe(201);
  });

  test('testEndpoint handles axios error with response payload and computes error timing', async () => {
    const svc = new ApiService({ ...baseConfig, timeout: undefined }); // fallback 30000
    const endpoint = getEndpoint();

    setNowSequence([1000, 1050, 1200]); // start, prep, error end

    const error = {
      message: 'Request failed with status code 500',
      code: 'ERR_BAD_RESPONSE',
      response: { status: 500, data: { err: 'boom' } },
      isAxiosError: true,
    };
    mockedAxios.mockRejectedValueOnce(error);

    const result = await svc.testEndpoint(endpoint);

    const cfg: AxiosRequestConfig = mockedAxios.mock.calls[0][0];
    expect(cfg.timeout).toBe(30000); // default fallback

    expect(result.status).toBe('error');
    expect(result.statusCode).toBe(500);
    expect(result.response).toEqual({ err: 'boom' });
    expect(result.error).toContain('status code 500');

    // requestTime = 50, responseTime = 1200 - (1000+50) = 150, totalTime=200
    expect(result.requestTime).toBe(50);
    expect(result.responseTime).toBe(150);
    expect(result.totalTime).toBe(200);
  });

  test('testEndpoint marks timeout when axios error code is ECONNABORTED', async () => {
    const svc = new ApiService(baseConfig);
    const endpoint = getEndpoint();

    setNowSequence([2000, 2300, 2600]);

    const timeoutErr = {
      message: 'timeout of 5000ms exceeded',
      code: 'ECONNABORTED',
      response: undefined,
      isAxiosError: true,
    };
    mockedAxios.mockRejectedValueOnce(timeoutErr);

    const result = await svc.testEndpoint(endpoint);

    expect(result.status).toBe('timeout'); // special-case mapping
    expect(result.statusCode).toBeUndefined();
    expect(result.error).toContain('timeout');
  });

  test('cancelCurrentRequests aborts in-flight axios call (ERR_CANCELED)', async () => {
    const svc = new ApiService(baseConfig);
    const endpoint = getEndpoint();

    // Arrange axios to reject when the passed AbortSignal is aborted
    mockedAxios.mockImplementationOnce((cfg: AxiosRequestConfig) => {
      return new Promise((_, reject) => {
        const signal = (cfg as any).signal as AbortSignal | undefined;
        if (signal) {
          signal.addEventListener('abort', () => {
            reject({ message: 'canceled', code: 'ERR_CANCELED', isAxiosError: true });
          });
        }
      });
    });

    // kick off the request (don't await yet)
    const promise = svc.testEndpoint(endpoint);
    // cancel immediately
    svc.cancelCurrentRequests();

    const result = await promise;

    expect(result.status).toBe('error'); // not timeout; cancel is treated as generic error
    expect(result.error?.toLowerCase()).toContain('canceled');
  });

  test('updateConfig applies to subsequent requests (baseUrl + timeout change)', async () => {
    const svc = new ApiService({ ...baseConfig, baseUrl: 'https://old.example.com', timeout: 1000 });
    mockedAxios.mockResolvedValue({ status: 200, data: { ok: true }, headers: {} });

    await svc.testEndpoint(getEndpoint({ path: '/p1' }));
    let cfg: AxiosRequestConfig = mockedAxios.mock.calls[0][0];
    expect(cfg.url).toBe('https://old.example.com/p1');
    expect(cfg.timeout).toBe(1000);

    svc.updateConfig({ ...baseConfig, baseUrl: 'https://new.example.com', timeout: 7000 });
    await svc.testEndpoint(getEndpoint({ path: '/p2' }));
    cfg = mockedAxios.mock.calls[1][0];
    expect(cfg.url).toBe('https://new.example.com/p2');
    expect(cfg.timeout).toBe(7000);
  });

  test('testMultipleEndpoints sequential mode (concurrency=1) reports progress per item and preserves order', async () => {
    const svc = new ApiService({ ...baseConfig, concurrency: 1 });
    const endpoints = [
      getEndpoint({ name: 'A', path: '/a' }),
      getEndpoint({ name: 'B', path: '/b' }),
    ];

    mockedAxios
      .mockResolvedValueOnce({ status: 200, data: { a: 1 }, headers: {} })
      .mockResolvedValueOnce({ status: 200, data: { b: 2 }, headers: {} });

    const onProgress = jest.fn();
    const onComplete = jest.fn();

    const results = await svc.testMultipleEndpoints(endpoints, onProgress, onComplete);

    expect(results).toHaveLength(2);
    expect(results[0].endpoint.name).toBe('A');
    expect(results[1].endpoint.name).toBe('B');

    expect(onProgress).toHaveBeenNthCalledWith(
      1,
      (1 / 2) * 100,
      expect.objectContaining({ endpoint: expect.objectContaining({ name: 'A' }) })
    );
    expect(onProgress).toHaveBeenNthCalledWith(
      2,
      (2 / 2) * 100,
      expect.objectContaining({ endpoint: expect.objectContaining({ name: 'B' }) })
    );

    expect(onComplete).toHaveBeenCalledWith(results);
  });

  test('testMultipleEndpoints concurrent mode chunks by concurrency and reports progress after each chunk', async () => {
    const svc = new ApiService({ ...baseConfig, concurrency: 2 });

    const endpoints = [
      getEndpoint({ name: 'E1', path: '/e1' }),
      getEndpoint({ name: 'E2', path: '/e2' }),
      getEndpoint({ name: 'E3', path: '/e3' }),
      getEndpoint({ name: 'E4', path: '/e4' }),
      getEndpoint({ name: 'E5', path: '/e5' }),
    ];

    // Resolve all quickly
    mockedAxios.mockResolvedValue({ status: 200, data: { ok: true }, headers: {} });

    const onProgress = jest.fn();

    const results = await svc.testMultipleEndpoints(endpoints, onProgress);

    expect(results).toHaveLength(5);

    // Expect 3 chunks: [E1,E2], [E3,E4], [E5]
    // Progress called with % = resultsSoFar / total * 100, and last result of chunk
    expect(onProgress).toHaveBeenCalledTimes(3);
    expect(onProgress).toHaveBeenNthCalledWith(
      1,
      (2 / 5) * 100,
      expect.objectContaining({ endpoint: expect.objectContaining({ name: 'E2' }) })
    );
    expect(onProgress).toHaveBeenNthCalledWith(
      2,
      (4 / 5) * 100,
      expect.objectContaining({ endpoint: expect.objectContaining({ name: 'E4' }) })
    );
    expect(onProgress).toHaveBeenNthCalledWith(
      3,
      (5 / 5) * 100,
      expect.objectContaining({ endpoint: expect.objectContaining({ name: 'E5' }) })
    );
  });

  test('testWithRetries returns success on subsequent attempt without waiting (delay mocked)', async () => {
    const svc = new ApiService({ ...baseConfig, retries: 3 });

    // 1st attempt -> error result; 2nd attempt -> success
    mockedAxios
      .mockRejectedValueOnce({ message: 'network', isAxiosError: true })
      .mockResolvedValueOnce({ status: 200, data: { ok: true }, headers: {} });

    // Mock private delay to avoid actual waiting
    const delaySpy = jest.spyOn(ApiService.prototype as any, 'delay').mockResolvedValue(undefined);

    const endpoint = getEndpoint();
    const res = await svc.testWithRetries(endpoint);

    expect(res.status).toBe('success');
    expect(delaySpy).toHaveBeenCalledTimes(1);
  });

  test('testWithRetries returns last error result when all attempts fail', async () => {
    const svc = new ApiService({ ...baseConfig, retries: 2 });

    mockedAxios
      .mockRejectedValueOnce({ message: 'fail-1', isAxiosError: true })
      .mockRejectedValueOnce({ message: 'fail-2', isAxiosError: true });

    jest.spyOn(ApiService.prototype as any, 'delay').mockResolvedValue(undefined);

    const endpoint = getEndpoint();
    const res = await svc.testWithRetries(endpoint);

    expect(res.status).toBe('error');
    expect(res.error).toContain('fail-2'); // last result bubbled
  });
});