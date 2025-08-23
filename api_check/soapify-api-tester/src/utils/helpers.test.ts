/**
 * Unit tests for helpers.ts
 * Testing framework detected via globals:
 * - Primary: Jest or Vitest (auto-detected using globalThis.vi || globalThis.jest)
 * These tests avoid framework-specific imports and should run under either environment.
 */

import {
  generateId,
  formatDuration,
  formatFileSize,
  formatDateTime,
  calculateResponseAccuracy,
  calculateStatistics,
  saveResumeData,
  loadResumeData,
  clearResumeData,
  exportResults,
  exportResultsCSV,
  deepClone,
  debounce,
  throttle,
  getStatusColor,
  getAccuracyColor,
  isValidUrl,
  generateTestPayload,
} from './helpers';

// Resolve jest/vi at runtime for compatibility
declare const jest: any;
declare const vi: any;
const J: any = (globalThis as any).vi ?? (globalThis as any).jest ?? {
  // ultra-minimal fallbacks to reduce runtime errors if neither exists
  fn: (impl?: any) => {
    const calls: any[] = [];
    const mockFn = (...args: any[]) => {
      calls.push(args);
      return impl?.(...args);
    };
    (mockFn as any).mock = { calls };
    (mockFn as any).mockImplementation = (i: any) => (impl = i);
    (mockFn as any).mockReturnValue = (v: any) => (impl = () => v);
    return mockFn as any;
  },
  spyOn: (obj: any, key: string) => {
    const original = obj[key];
    const mock = J.fn();
    obj[key] = mock;
    (mock as any).mockRestore = () => (obj[key] = original);
    return mock;
  },
  useFakeTimers: () => {},
  useRealTimers: () => {},
  advanceTimersByTime: () => {},
  clearAllTimers: () => {},
  restoreAllMocks: () => {},
};

// Aliases for timer methods to avoid being mistaken as React hooks
const { useFakeTimers: fakeTimers, useRealTimers: realTimers, advanceTimersByTime: advanceTimers, restoreAllMocks: restoreMocks } = J;

declare var document: any;
declare var Blob: any;
declare var URL: any;

const originalGlobals = {
  DateNow: Date.now,
  MathRandom: Math.random,
  localStorage: (globalThis as any).localStorage,
  document: (globalThis as any).document,
  URL: (globalThis as any).URL,
  Blob: (globalThis as any).Blob,
  consoleError: console.error,
};

afterEach(() => {
  // Restore globals after each test
  Date.now = originalGlobals.DateNow;
  Math.random = originalGlobals.MathRandom;
  (globalThis as any).localStorage = originalGlobals.localStorage;
  (globalThis as any).document = originalGlobals.document;
  (globalThis as any).URL = originalGlobals.URL;
  (globalThis as any).Blob = originalGlobals.Blob;
  console.error = originalGlobals.consoleError;

  // Restore timers/mocks if available
  try { realTimers?.(); } catch {}
  try { restoreMocks?.(); } catch {}
});

function createMockLocalStorage(initial: Record<string, string> = {}) {
  const store = new Map<string, string>(Object.entries(initial));
  return {
    getItem: J.fn((k: string) => (store.has(k) ? store.get(k)! : null)),
    setItem: J.fn((k: string, v: string) => { store.set(k, v); }),
    removeItem: J.fn((k: string) => { store.delete(k); }),
    clear: J.fn(() => { store.clear(); }),
    _store: store,
  };
}

class MockBlob {
  parts: any[];
  options?: any;
  constructor(parts: any[], options?: any) {
    this.parts = parts;
    this.options = options;
  }
}

function withMockDOM() {
  const anchor = {
    href: '',
    download: '',
    click: J.fn(),
  };
  const mockDoc = {
    createElement: J.fn((tag: string) => (tag === 'a' ? anchor : ({ tag } as any))),
    body: {
      appendChild: J.fn(),
      removeChild: J.fn(),
    },
  };
  const mockURL = {
    createObjectURL: J.fn(() => 'blob:mock-url'),
    revokeObjectURL: J.fn(),
  };
  (globalThis as any).document = mockDoc;
  (globalThis as any).URL = mockURL;
  (globalThis as any).Blob = MockBlob as any;

  return { anchor, mockDoc, mockURL };
}

describe('generateId', () => {
  test('generates unique hyphenated ids with base36 suffix of length 9', () => {
    const id1 = generateId();
    const id2 = generateId();
    expect(id1).not.toEqual(id2);
    expect(id1).toMatch(/^\d+-[a-z0-9]{9}$/);
    expect(id2).toMatch(/^\d+-[a-z0-9]{9}$/);
  });
});

describe('formatDuration', () => {
  test('returns ms for durations under 1000ms', () => {
    expect(formatDuration(0)).toBe('0ms');
    expect(formatDuration(500)).toBe('500ms');
    expect(formatDuration(999)).toBe('999ms');
  });

  test('formats seconds correctly', () => {
    expect(formatDuration(1000)).toBe('1s');
    expect(formatDuration(1500)).toBe('1s');
    expect(formatDuration(59000)).toBe('59s');
  });

  test('formats minutes and seconds correctly', () => {
    expect(formatDuration(60000)).toBe('1m 0s');
    expect(formatDuration(65000)).toBe('1m 5s');
  });

  test('formats hours, minutes, and seconds correctly', () => {
    expect(formatDuration(3 * 3600000 + 65 * 1000)).toBe('3h 1m 5s');
  });
});

describe('formatFileSize', () => {
  test('handles zero bytes', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
  });
  test('handles bytes under 1KB', () => {
    expect(formatFileSize(500)).toBe('500 Bytes');
  });
  test('handles 1KB boundary and rounding', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });
});

describe('formatDateTime', () => {
  test('delegates to Date.prototype.toLocaleString with en-US options', () => {
    const spy = J.spyOn(Date.prototype as any, 'toLocaleString').mockReturnValue('MOCKED');
    const dt = new Date('2025-06-01T20:30:15Z');
    const out = formatDateTime(dt);
    expect(out).toBe('MOCKED');
    spy.mockRestore?.();
  });
});

describe('calculateResponseAccuracy', () => {
  test('returns 0 for type mismatch', () => {
    expect(calculateResponseAccuracy('a', 1)).toBe(0);
  });

  test('handles primitives', () => {
    expect(calculateResponseAccuracy('a', 'a')).toBe(100);
    expect(calculateResponseAccuracy('a', 'b')).toBe(0);
    expect(calculateResponseAccuracy(5, 5)).toBe(100);
    expect(calculateResponseAccuracy(true, false)).toBe(0);
  });

  test('handles arrays with length mismatch penalty', () => {
    expect(calculateResponseAccuracy([1, 2, 3], [1, 2])).toBe(90);
    expect(calculateResponseAccuracy([1], [1, 2, 3])).toBe(80);
  });

  test('handles arrays of equal length by element match ratio', () => {
    const acc = calculateResponseAccuracy([1, 2, 3], [1, 2, 4]);
    expect(acc).toBeCloseTo((2 / 3) * 100, 6);
  });

  test('handles objects with missing and extra keys (penalty applied)', () => {
    const expected = { a: 1, b: 2 };
    const actual = { a: 1, b: 2, c: 3 };
    expect(calculateResponseAccuracy(expected, actual)).toBe(95); // 100 avg - 5 penalty for extra key
  });

  test('handles nested objects', () => {
    const expected = { a: { x: 1, y: 2 } };
    const actualGood = { a: { x: 1, y: 2 } };
    const actualMixed = { a: { x: 1, y: 3 } };
    expect(calculateResponseAccuracy(expected, actualGood)).toBe(100);
    expect(calculateResponseAccuracy(expected, actualMixed)).toBe(50);
  });
});

describe('calculateStatistics', () => {
  test('returns zeroed stats for empty input', () => {
    expect(calculateStatistics([] as any)).toEqual({
      totalRequests: 0,
      successRate: 0,
      averageResponseTime: 0,
      minResponseTime: 0,
      maxResponseTime: 0,
      errorRate: 0,
      throughput: 0,
      categoriesStats: {},
    });
  });

  test('computes aggregate statistics and per-category averages', () => {
    const t0 = new Date('2025-08-01T00:00:00.000Z');
    const t1 = new Date('2025-08-01T00:00:02.000Z');
    const t2 = new Date('2025-08-01T00:00:05.000Z');

    const results: any[] = [
      {
        status: 'success',
        totalTime: 120,
        requestTime: 20,
        responseTime: 100,
        timestamp: t0,
        endpoint: { name: 'Login', method: 'POST', path: '/auth', category: 'auth' },
      },
      {
        status: 'error',
        totalTime: 240,
        requestTime: 40,
        responseTime: 200,
        timestamp: t1,
        endpoint: { name: 'GetUser', method: 'GET', path: '/users/1', category: 'user' },
      },
      {
        status: 'success',
        totalTime: 60,
        requestTime: 10,
        responseTime: 50,
        timestamp: t2,
        endpoint: { name: 'GetUser', method: 'GET', path: '/users/2', category: 'user' },
      },
    ];

    const stats = calculateStatistics(results as any);
    expect(stats.totalRequests).toBe(3);
    expect(stats.successRate).toBeCloseTo((2 / 3) * 100, 5);
    expect(stats.averageResponseTime).toBeCloseTo((120 + 240 + 60) / 3, 6);
    expect(stats.minResponseTime).toBe(60);
    expect(stats.maxResponseTime).toBe(240);
    expect(stats.errorRate).toBeCloseTo((1 / 3) * 100, 5);
    // throughput = 3 requests / (5s span)
    expect(stats.throughput).toBeCloseTo(0.6, 6);

    // Category totals and average
    expect(stats.categoriesStats['auth']).toBeDefined();
    expect(stats.categoriesStats['auth'].total).toBe(1);
    expect(stats.categoriesStats['auth'].successful).toBe(1);
    expect(stats.categoriesStats['auth'].failed).toBe(0);
    expect(stats.categoriesStats['auth'].averageTime).toBe(120);

    expect(stats.categoriesStats['user']).toBeDefined();
    expect(stats.categoriesStats['user'].total).toBe(2);
    expect(stats.categoriesStats['user'].successful).toBe(1);
    expect(stats.categoriesStats['user'].failed).toBe(1);
    expect(stats.categoriesStats['user'].averageTime).toBe((240 + 60) / 2);
  });
});

describe('resume data persistence (save/load/clear)', () => {
  test('saves and loads resume data including last_session_id', () => {
    const mockLS = createMockLocalStorage();
    (globalThis as any).localStorage = mockLS;

    const sessionId = 'sess-abc';
    const partialResults: any[] = [
      { status: 'success', totalTime: 10, timestamp: new Date(), endpoint: { category: 'cat' } },
    ];

    Date.now = () => 1234567890;
    saveResumeData(sessionId, 5, { foo: 'bar' }, partialResults as any);

    expect(mockLS.setItem).toHaveBeenCalledTimes(2);
    expect(mockLS.setItem.mock.calls[0][0]).toBe();
    expect(mockLS.setItem.mock.calls[1]).toEqual(['last_session_id', sessionId]);

    const loaded = loadResumeData(sessionId);
    expect(loaded).not.toBeNull();
    expect(loaded!.sessionId).toBe(sessionId);
    expect(loaded!.lastCompletedIndex).toBe(5);
    expect(loaded!.config).toEqual({ foo: 'bar' });
    expect(Array.isArray(loaded!.partialResults)).toBe(true);
    expect(loaded!.timestamp instanceof Date).toBe(true);

    // load without passing sessionId should use last_session_id
    const loaded2 = loadResumeData();
    expect(loaded2?.sessionId).toBe(sessionId);
  });

  test('handles storage exceptions gracefully in save/load/clear', () => {
    const mockLS = createMockLocalStorage();
    (globalThis as any).localStorage = mockLS;

    const err = new Error('quota exceeded');
    mockLS.setItem.mockImplementationOnce(() => { throw err; });
    console.error = J.fn();

    saveResumeData('sess-x', 0, {}, [] as any);
    expect(console.error).toHaveBeenCalled();

    // Malformed JSON during load
    mockLS.getItem.mockImplementationOnce(() => 'not-json');
    console.error = J.fn();
    const out = loadResumeData('sess-x');
    expect(out).toBeNull();
    expect(console.error).toHaveBeenCalled();

    // clear removes both keys when session matches last_session_id
    mockLS._store.set('resume_sess-x', '{}');
    mockLS._store.set('last_session_id', 'sess-x');
    clearResumeData('sess-x');
    expect(mockLS.getItem('resume_sess-x')).toBeNull();
    expect(mockLS.getItem('last_session_id')).toBeNull();
  });
});

describe('exportResults and exportResultsCSV', () => {
  test('exportResults generates JSON blob and triggers anchor click', () => {
    const { anchor, mockDoc, mockURL } = withMockDOM();

    const session: any = {
      id: 'sess-123',
      results: [
        {
          status: 'success',
          statusCode: 200,
          requestTime: 10,
          responseTime: 90,
          totalTime: 100,
          timestamp: new Date('2025-08-20T00:00:00.000Z'),
          endpoint: { name: 'GetUsers', method: 'GET', path: '/users', category: 'user' },
          requestSize: 10,
          responseSize: 20,
          accuracyPercentage: 100,
          error: '',
        },
      ],
    };

    exportResults(session);

    expect(mockDoc.createElement).toHaveBeenCalledWith('a');
    expect(mockDoc.body.appendChild).toHaveBeenCalledWith(anchor);
    expect(anchor.click).toHaveBeenCalledTimes(1);
    expect(mockDoc.body.removeChild).toHaveBeenCalledWith(anchor);
    expect(mockURL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(mockURL.revokeObjectURL).toHaveBeenCalledTimes(1);

    // Validate download filename pattern
    expect(anchor.download).toMatch(/^api_test_results_sess-123_\d{4}-\d{2}-\d{2}\.json$/);

    // Validate blob content shape
    const passedBlob = (mockURL.createObjectURL as any).mock.calls[0][0];
    expect(passedBlob).toBeInstanceOf(MockBlob);
    const text = (passedBlob as any).parts[0] as string;
    const parsed = JSON.parse(text);
    expect(parsed).toHaveProperty('session');
    expect(parsed).toHaveProperty('statistics');
    expect(parsed.session.results[0].timestamp).toBe('2025-08-20T00:00:00.000Z');
    expect(parsed).toHaveProperty('exportedAt');
  });

  test('exportResultsCSV generates CSV blob with header row', () => {
    const { anchor, mockDoc, mockURL } = withMockDOM();

    const results: any[] = [
      {
        status: 'error',
        statusCode: 500,
        requestTime: 20,
        responseTime: 80,
        totalTime: 100,
        timestamp: new Date('2025-08-21T12:00:00.000Z'),
        endpoint: { name: 'CreateUser', method: 'POST', path: '/users', category: 'user' },
        requestSize: 50,
        responseSize: 0,
        accuracyPercentage: 0,
        error: 'Internal Server Error',
      },
    ];

    exportResultsCSV(results as any);

    expect(mockDoc.createElement).toHaveBeenCalledWith('a');
    expect(anchor.click).toHaveBeenCalledTimes(1);
    expect(anchor.download).toMatch(/^api_test_results_\d{4}-\d{2}-\d{2}\.csv$/);

    const passedBlob = (mockURL.createObjectURL as any).mock.calls[0][0];
    expect(passedBlob).toBeInstanceOf(MockBlob);
    const csv = (passedBlob as any).parts[0] as string;
    expect(csv.startsWith('Timestamp,Endpoint Name,Method,Path,Category,Status,Status Code,Request Time (ms),Response Time (ms),Total Time (ms),Request Size (bytes),Response Size (bytes),Accuracy (%),Error Message')).toBe(true);
    expect(csv).toContain('CreateUser');
    expect(csv).toContain('POST');
    expect(csv).toContain('/users');
  });
});

describe('deepClone', () => {
  test('returns primitives unchanged', () => {
    expect(deepClone(null as any)).toBeNull();
    expect(deepClone(42 as any)).toBe(42);
    expect(deepClone('x' as any)).toBe('x');
    expect(deepClone(true as any)).toBe(true);
  });

  test('clones Date objects', () => {
    const d = new Date('2024-01-01T00:00:00.000Z');
    const c = deepClone(d);
    expect(c).not.toBe(d);
    expect(c.getTime()).toBe(d.getTime());
  });

  test('deeply clones arrays and objects', () => {
    const original = { a: 1, b: { c: [1, 2, { d: 'z' }] } };
    const cloned = deepClone(original);
    expect(cloned).toEqual(original);
    // mutate clone and ensure original unaffected
    (cloned as any).b.c[2].d = 'changed';
    expect(original.b.c[2].d).toBe('z');
  });
});

describe('debounce', () => {
  test('calls function once after wait with latest arguments', () => {
    fakeTimers?.();
    const fn = J.fn();
    const debounced = debounce(fn, 100);

    debounced('first');
    debounced('second');

    expect(fn).not.toHaveBeenCalled();
    advanceTimers?.(99);
    expect(fn).not.toHaveBeenCalled();
    advanceTimers?.(1);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('second');

    realTimers?.();
  });
});

describe('throttle', () => {
  test('executes immediately then throttles subsequent calls within limit', () => {
    fakeTimers?.();
    const fn = J.fn();
    const throttled = throttle(fn, 100);

    throttled('a'); // immediate
    throttled('b'); // throttled
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('a');

    advanceTimers?.(99);
    throttled('c'); // still throttled
    expect(fn).toHaveBeenCalledTimes(1);

    advanceTimers?.(1);
    throttled('d'); // allowed after window
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenCalledWith('d');

    realTimers?.();
  });
});

describe('UI colors', () => {
  test('getStatusColor returns expected hex values', () => {
    expect(getStatusColor('success')).toBe('#10b981');
    expect(getStatusColor('error')).toBe('#ef4444');
    expect(getStatusColor('timeout')).toBe('#f59e0b');
    expect(getStatusColor('pending')).toBe('#6b7280');
    expect(getStatusColor('unknown')).toBe('#6b7280');
  });

  test('getAccuracyColor thresholds', () => {
    expect(getAccuracyColor(95)).toBe('#10b981'); // >= 90
    expect(getAccuracyColor(70)).toBe('#f59e0b'); // >= 70
    expect(getAccuracyColor(50)).toBe('#f97316'); // >= 50
    expect(getAccuracyColor(49)).toBe('#ef4444'); // < 50
  });
});

describe('isValidUrl', () => {
  test('validates absolute URLs', () => {
    expect(isValidUrl('https://example.com/path?x=1')).toBe(true);
    expect(isValidUrl('http://localhost:8080')).toBe(true);
  });
  test('rejects invalid/relative URLs', () => {
    expect(isValidUrl('not a url')).toBe(false);
    expect(isValidUrl('/relative/path')).toBe(false);
  });
});

describe('generateTestPayload', () => {
  test('returns undefined when endpoint has no payload', () => {
    expect(generateTestPayload({} as any)).toBeUndefined();
  });

  test('generates deterministic payload for known field types', () => {
    // Stabilize randomness and time
    Date.now = () => 1717171717171;
    Math.random = () => 0.7; // > 0.5 => true; number -> 70

    // Ensure Blob exists for 'file' type
    (globalThis as any).Blob = MockBlob as any;

    const endpoint = {
      payload: {
        username: 'string',
        age: 'number',
        active: 'boolean',
        tags: 'array',
        meta: 'object',
        attachment: 'file',
        custom: 'customType',
      },
    };

    const payload: any = generateTestPayload(endpoint as any);
    expect(payload.username).toMatch(/^test_username_\d+$/);
    expect(payload.age).toBe(70);
    expect(payload.active).toBe(true);
    expect(Array.isArray(payload.tags)).toBe(true);
    expect(payload.meta).toEqual({ test: 'data' });
    expect(payload.attachment).toBeInstanceOf(MockBlob);
    expect(typeof payload.custom).toBe('string');
    expect(payload.custom).toMatch(/^test_customType_\d+$/);
  });
});