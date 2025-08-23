/**
 * Framework: Jest (via react-scripts test)
 * Focus: Unit tests for ApiService (happy paths, edge cases, failures, concurrency, retries, cancellation)
 * Notes:
 * - axios is mocked as a callable default export with isAxiosError attached.
 * - helper utilities are mocked for deterministic IDs and accuracy calculations.
 */

jest.mock('axios', () => {
  const axiosFn = jest.fn();
  axiosFn.isAxiosError = jest.fn();
  return axiosFn;
});

jest.mock('../../utils/helpers', () => ({
  generateId: jest.fn(() => 'fixed-test-id'),
  calculateResponseAccuracy: jest.fn(() => 88.5),
}));

import axios from 'axios';
import ApiService from '../apiService';
import { calculateResponseAccuracy } from '../../utils/helpers';

const asAny = <T>(v: unknown) => v as unknown as T;

describe('ApiService (Jest)', () => {
  const baseConfig: any = {
    baseUrl: 'https://api.example.com',
    timeout: 5000,
    concurrency: 1,
    retries: 1,
    customHeaders: { 'X-App': 'Tester' },
    authToken: 'abc123',
  };

  const okResponse = (data: unknown = { ok: true }, status = 200): any => ({
    data,
    status,
    statusText: 'OK',
    headers: { 'x-response': 'yes' },
    config: {},
  });

  beforeEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  describe('testEndpoint - success path', () => {
    it('returns success with timing, sizes, statusCode, and accuracy when expected_response is provided', async () => {
      asAny(axios).mockResolvedValueOnce(okResponse({ result: 'value' }, 201));
      const service = new ApiService(baseConfig);

      const abortInstance = { abort: jest.fn(), signal: { mocked: true } };
      const RealAbort = (global as any).AbortController;
      (global as any).AbortController = jest.fn(() => abortInstance);

      const endpoint: any = {
        name: 'Create Thing',
        method: 'POST',
        path: '/v1/things',
        payload: { a: 1 },
        query_params: { q: 'z' },
        headers: { 'X-Endpoint': 'yes' },
        auth_required: true,
        expected_response: { success: true },
      };

      const result = await service.testEndpoint(endpoint);

      (global as any).AbortController = RealAbort;

      expect(result.id).toBe('fixed-test-id');
      expect(result.status).toBe('success');
      expect(result.statusCode).toBe(201);
      expect(result.response).toEqual({ result: 'value' });
      expect(result.actualResponse).toEqual({ result: 'value' });
      expect(result.timestamp instanceof Date).toBe(true);

      expect(result.requestTime).toBeGreaterThanOrEqual(0);
      expect(result.responseTime).toBeGreaterThanOrEqual(0);
      expect(result.totalTime).toBeGreaterThanOrEqual(result.requestTime + result.responseTime);

      expect(calculateResponseAccuracy).toHaveBeenCalledWith(
        endpoint.expected_response,
        { result: 'value' }
      );
      expect(result.accuracyPercentage).toBe(88.5);

      expect(asAny(axios).mock.calls.length).toBe(1);
      const sentConfig = asAny(axios).mock.calls[0][0] as any;
      expect(sentConfig.method).toBe('POST');
      expect(sentConfig.url).toBe('https://api.example.com/v1/things');
      expect(sentConfig.timeout).toBe(5000);
      expect(sentConfig.signal).toBe(abortInstance.signal);
      expect(sentConfig.data).toEqual({ a: 1 });
      expect(sentConfig.params).toEqual({ q: 'z' });
      expect(sentConfig.headers).toMatchObject({
        'Content-Type': 'application/json',
        'X-App': 'Tester',
        'X-Endpoint': 'yes',
        Authorization: 'Bearer abc123',
      });

      const expectedReqSize =
        JSON.stringify(sentConfig.headers).length +
        JSON.stringify(sentConfig.data).length +
        (sentConfig.url || '').length +
        JSON.stringify(sentConfig.params).length;
      expect(result.requestSize).toBe(expectedReqSize);

      const expectedRespSize =
        JSON.stringify(okResponse({ result: 'value' }).headers).length +
        JSON.stringify({ result: 'value' }).length;
      expect(result.responseSize).toBe(expectedRespSize);
    });

    it('omits payload for GET requests and does not attach Authorization when auth not required', async () => {
      asAny(axios).mockResolvedValueOnce(okResponse({ ok: true }, 200));
      const service = new ApiService({ ...baseConfig });

      const endpoint: any = {
        name: 'Fetch',
        method: 'GET',
        path: '/v1/list',
        payload: { ignored: true },
        auth_required: false,
      };

      const result = await service.testEndpoint(endpoint);
      expect(result.status).toBe('success');

      const sentConfig = asAny(axios).mock.calls[0][0] as any;
      expect(sentConfig.method).toBe('GET');
      expect(sentConfig.data).toBeUndefined();
      expect(sentConfig.headers).not.toHaveProperty('Authorization');
    });
  });

  describe('testEndpoint - error handling', () => {
    it('handles AxiosError with response and sets status=error', async () => {
      const axiosErr = {
        isAxiosError: true,
        message: 'Request failed',
        response: { status: 400, data: { error: 'bad' } },
        code: 'ERR_BAD_REQUEST',
      };
      asAny(axios).isAxiosError.mockReturnValue(true);
      asAny(axios).mockRejectedValueOnce(axiosErr);

      const service = new ApiService(baseConfig);
      const endpoint: any = { name: 'Bad', method: 'POST', path: '/bad' };

      const result = await service.testEndpoint(endpoint);
      expect(result.status).toBe('error');
      expect(result.statusCode).toBe(400);
      expect(result.error).toBe('Request failed');
      expect(result.response).toEqual({ error: 'bad' });
      expect(result.responseTime).toBeGreaterThanOrEqual(0);
      expect(result.totalTime).toBeGreaterThanOrEqual(0);
    });

    it('treats ECONNABORTED as timeout', async () => {
      const axiosErr = {
        isAxiosError: true,
        message: 'timeout',
        response: { status: 504, data: { t: true } },
        code: 'ECONNABORTED',
      };
      asAny(axios).isAxiosError.mockReturnValue(true);
      asAny(axios).mockRejectedValueOnce(axiosErr);

      const service = new ApiService(baseConfig);
      const endpoint: any = { name: 'Timeout', method: 'GET', path: '/slow' };

      const result = await service.testEndpoint(endpoint);
      expect(result.status).toBe('timeout');
      expect(result.statusCode).toBe(504);
      expect(result.error).toBe('timeout');
      expect(result.response).toEqual({ t: true });
    });

    it('handles non-Axios errors gracefully', async () => {
      asAny(axios).isAxiosError.mockReturnValue(false);
      asAny(axios).mockRejectedValueOnce(new Error('boom'));

      const service = new ApiService(baseConfig);
      const endpoint: any = { name: 'NonAxios', method: 'GET', path: '/err' };

      const result = await service.testEndpoint(endpoint);
      expect(result.status).toBe('error');
      expect(result.error).toBe('boom');
    });
  });

  describe('testMultipleEndpoints', () => {
    it('runs sequentially when concurrency=1 and reports progress for each', async () => {
      asAny(axios)
        .mockResolvedValueOnce(okResponse({ i: 1 }))
        .mockResolvedValueOnce(okResponse({ i: 2 }))
        .mockResolvedValueOnce(okResponse({ i: 3 }));

      const service = new ApiService({ ...baseConfig, concurrency: 1 });
      const endpoints: any[] = [
        { name: 'e1', method: 'GET', path: '/1' },
        { name: 'e2', method: 'GET', path: '/2' },
        { name: 'e3', method: 'GET', path: '/3' },
      ];

      const onProgress = jest.fn();
      const onComplete = jest.fn();

      const results = await service.testMultipleEndpoints(endpoints, onProgress, onComplete);

      expect(results).toHaveLength(3);
      expect(onProgress).toHaveBeenCalledTimes(3);
      const percents = onProgress.mock.calls.map((c: any[]) => c[0]);
      expect(percents[0]).toBeCloseTo((1 / 3) * 100, 3);
      expect(percents[1]).toBeCloseTo((2 / 3) * 100, 3);
      expect(percents[2]).toBeCloseTo(100, 3);
      expect(onComplete).toHaveBeenCalledWith(results);
    });

    it('runs in chunks when concurrency>1 and reports progress per chunk', async () => {
      asAny(axios)
        .mockResolvedValueOnce(okResponse({ i: 1 }))
        .mockResolvedValueOnce(okResponse({ i: 2 }))
        .mockResolvedValueOnce(okResponse({ i: 3 }))
        .mockResolvedValueOnce(okResponse({ i: 4 }));

      const service = new ApiService({ ...baseConfig, concurrency: 2 });
      const endpoints: any[] = [
        { name: 'e1', method: 'GET', path: '/1' },
        { name: 'e2', method: 'GET', path: '/2' },
        { name: 'e3', method: 'GET', path: '/3' },
        { name: 'e4', method: 'GET', path: '/4' },
      ];

      const onProgress = jest.fn();
      const results = await service.testMultipleEndpoints(endpoints, onProgress);

      expect(results).toHaveLength(4);
      expect(onProgress).toHaveBeenCalledTimes(2);
      expect(onProgress.mock.calls[0][0]).toBeCloseTo(50, 3);
      expect(onProgress.mock.calls[1][0]).toBeCloseTo(100, 3);
    });
  });

  describe('testWithRetries', () => {
    it('retries on error and succeeds on a later attempt; uses exponential backoff via delay()', async () => {
      const axiosErr = { isAxiosError: true, message: 'fail', code: 'ERR', response: { status: 500, data: {} } };
      asAny(axios).isAxiosError.mockReturnValue(true);
      asAny(axios)
        .mockRejectedValueOnce(axiosErr)
        .mockRejectedValueOnce(axiosErr)
        .mockResolvedValueOnce(okResponse({ ok: true }, 200));

      const service = new ApiService({ ...baseConfig, retries: 3 });

      const delaySpy = jest
        // @ts-expect-error access private method
        .spyOn(asAny(service), 'delay')
        .mockResolvedValue();

      const endpoint: any = { name: 'retry', method: 'GET', path: '/retry' };
      const result = await service.testWithRetries(endpoint);

      expect(result.status).toBe('success');
      expect(delaySpy).toHaveBeenCalledTimes(2);
      expect(delaySpy).toHaveBeenNthCalledWith(1, 2 ** 1 * 1000);
      expect(delaySpy).toHaveBeenNthCalledWith(2, 2 ** 2 * 1000);
    });

    it('returns last error result when all attempts fail', async () => {
      const axiosErr = { isAxiosError: true, message: 'always bad', code: 'ERR', response: { status: 503, data: {} } };
      asAny(axios).isAxiosError.mockReturnValue(true);
      asAny(axios).mockRejectedValue(axiosErr);

      const service = new ApiService({ ...baseConfig, retries: 2 });
      jest.spyOn(asAny(service), 'delay').mockResolvedValue();

      const endpoint: any = { name: 'nope', method: 'GET', path: '/nope' };
      const result = await service.testWithRetries(endpoint);

      expect(result.status).toBe('error');
      expect(result.error).toBe('always bad');
      expect(result.statusCode).toBe(503);
    });
  });

  describe('updateConfig and cancelCurrentRequests', () => {
    it('updateConfig changes runtime behavior (e.g., timeout and headers)', async () => {
      asAny(axios).mockResolvedValueOnce(okResponse({ ok: true }));

      const service = new ApiService({ ...baseConfig, timeout: 1000, customHeaders: { A: '1' } });
      service.updateConfig({ ...baseConfig, timeout: 9001, customHeaders: { B: '2' } });

      const endpoint: any = { name: 'upd', method: 'POST', path: '/u', payload: { p: 1 } };
      await service.testEndpoint(endpoint);

      const sentConfig = asAny(axios).mock.calls[0][0] as any;
      expect(sentConfig.timeout).toBe(9001);
      expect(sentConfig.headers).toMatchObject({ B: '2' });
      expect(sentConfig.headers).not.toHaveProperty('A');
    });

    it('cancelCurrentRequests aborts when controller exists and is a no-op otherwise', async () => {
      asAny(axios).mockResolvedValueOnce(okResponse({ ok: true }));
      const service = new ApiService(baseConfig);

      const abortInstance = { abort: jest.fn(), signal: { mocked: true } };
      const RealAbort = (global as any).AbortController;
      (global as any).AbortController = jest.fn(() => abortInstance);

      await service.testEndpoint({ name: 'x', method: 'GET', path: '/x' });
      service.cancelCurrentRequests();
      expect(abortInstance.abort).toHaveBeenCalledTimes(1);

      // @ts-expect-error force undefined
      asAny(service).abortController = undefined;
      expect(() => service.cancelCurrentRequests()).not.toThrow();

      (global as any).AbortController = RealAbort;
    });
  });

  describe('request size calculation indirect check', () => {
    it('request size reflects presence/absence of params and headers', async () => {
      asAny(axios).mockResolvedValueOnce(okResponse({ ok: 1 }));
      const service = new ApiService({ ...baseConfig, customHeaders: {} });

      const endpoint: any = {
        name: 'calc',
        method: 'POST',
        path: '/calc',
        payload: { x: 10 },
        query_params: undefined,
        headers: { H1: 'v' },
        auth_required: false,
      };

      const result = await service.testEndpoint(endpoint);

      const sent = asAny(axios).mock.calls[0][0] as any;
      const expectedReqSize =
        JSON.stringify(sent.headers || {}).length +
        JSON.stringify(sent.data || {}).length +
        (sent.url || '').length +
        JSON.stringify(sent.params || {}).length;

      expect(result.requestSize).toBe(expectedReqSize);
    });
  });
});