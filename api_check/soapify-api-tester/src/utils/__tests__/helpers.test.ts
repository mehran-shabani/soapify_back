/**
 * Test suite for utils/helpers
 * Framework: Jest (ts-jest) with jsdom environment assumed.
 * If the project uses Vitest, these tests should work with minimal changes.
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
} from '../helpers';

type Endpoint = {
  name: string;
  method: string;
  path: string;
  category: string;
};

type TestResult = {
  endpoint: Endpoint;
  status: 'success' | 'error' | 'timeout' | 'pending';
  statusCode?: number;
  requestTime: number;
  responseTime: number;
  totalTime: number;
  requestSize?: number;
  responseSize?: number;
  accuracyPercentage?: number;
  error?: string;
  timestamp: Date;
};

type TestSession = {
  id: string;
  name: string;
  startedAt: Date;
  results: TestResult[];
};

describe('helpers: generateId', () => {
  it('generates unique IDs that contain timestamp and random segment', () => {
    const id1 = generateId();
    const id2 = generateId();
    expect(id1).not.toEqual(id2);
    expect(id1).toMatch(/^\d{10,}-[a-z0-9]{9}$/);
  });
});

describe('helpers: formatDuration', () => {
  it('formats milliseconds under 1000 as ms', () => {
    expect(formatDuration(0)).toBe('0ms');
    expect(formatDuration(999)).toBe('999ms');
  });
  it('formats seconds under 60 as s', () => {
    expect(formatDuration(1000)).toBe('1s');
    expect(formatDuration(59000)).toBe('59s');
  });
  it('formats minutes correctly', () => {
    expect(formatDuration(61000)).toBe('1m 1s');
    expect(formatDuration(125000)).toBe('2m 5s');
  });
  it('formats hours correctly (with minutes and seconds mod 60)', () => {
    expect(formatDuration(3661000)).toBe('1h 1m 1s');
    // 2h 0m 5s
    expect(formatDuration(2 * 3600 * 1000 + 5000)).toBe('2h 0m 5s');
  });
});

describe('helpers: formatFileSize', () => {
  it('returns 0 Bytes for zero', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
  });
  it('formats bytes to KB/MB/GB with rounding to 2 decimals', () => {
    expect(formatFileSize(500)).toBe('500 Bytes');
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(1048576)).toBe('1 MB');
  });
});

describe('helpers: formatDateTime', () => {
  it('formats date in en-US with 2-digit components', () => {
    const d = new Date('2023-01-02T03:04:05Z');
    // Note: locale/timezone dependent; check for expected shape: MM/DD/YYYY, HH:MM:SS
    const text = formatDateTime(d);
    expect(text).toMatch(/\d{2}\/\d{2}\/\d{4}, \d{2}:\d{2}:\d{2}/);
  });
});

describe('helpers: calculateResponseAccuracy', () => {
  it('returns 0 when types differ', () => {
    expect(calculateResponseAccuracy('1', 1)).toBe(0);
  });
  it('compares primitives strictly', () => {
    expect(calculateResponseAccuracy('abc', 'abc')).toBe(100);
    expect(calculateResponseAccuracy('abc', 'def')).toBe(0);
    expect(calculateResponseAccuracy(5, 5)).toBe(100);
    expect(calculateResponseAccuracy(true, false)).toBe(0);
  });
  it('compares arrays by element with >50 threshold and accounts for length', () => {
    expect(calculateResponseAccuracy([1, 2, 3], [1, 2, 3])).toBe(100);
    // One element mismatched
    const score = calculateResponseAccuracy([1, 2, 3], [1, 9, 3]);
    expect(score).toBeCloseTo((2 / 3) * 100, 5);
    // Different lengths penalized
    expect(calculateResponseAccuracy([1, 2, 3, 4], [1, 2])).toBeLessThan(100);
  });
  it('compares nested objects, penalizing missing/extra keys', () => {
    const expected = { a: 1, b: { c: 'x', d: true } };
    const actualPerfect = { a: 1, b: { c: 'x', d: true } };
    const actualMissing = { a: 1, b: { c: 'x' } };
    const actualExtra = { a: 1, b: { c: 'x', d: true }, e: 5 };
    expect(calculateResponseAccuracy(expected, actualPerfect)).toBe(100);
    expect(calculateResponseAccuracy(expected, actualMissing)).toBeLessThan(100);
    expect(calculateResponseAccuracy(expected, actualExtra)).toBeLessThan(100);
  });
});

describe('helpers: calculateStatistics', () => {
  const baseEndpoint: Endpoint = { name: 'GetUser', method: 'GET', path: '/users/1', category: 'users' };
  const mkResult = (over: Partial<TestResult> = {}): TestResult => ({
    endpoint: baseEndpoint,
    status: 'success',
    requestTime: 10,
    responseTime: 20,
    totalTime: 30,
    timestamp: new Date('2023-01-01T00:00:00Z'),
    ...over,
  });

  it('returns zeros for empty results', () => {
    const stats = calculateStatistics([]);
    expect(stats.totalRequests).toBe(0);
    expect(stats.successRate).toBe(0);
    expect(stats.averageResponseTime).toBe(0);
    expect(stats.minResponseTime).toBe(0);
    expect(stats.maxResponseTime).toBe(0);
    expect(stats.errorRate).toBe(0);
    expect(stats.throughput).toBe(0);
    expect(stats.categoriesStats).toEqual({});
  });

  it('computes aggregates, success/error rates, and category stats', () => {
    const results: TestResult[] = [
      mkResult({ status: 'success', totalTime: 50, responseTime: 40, timestamp: new Date('2023-01-01T00:00:00Z'), endpoint: { ...baseEndpoint, category: 'users' } }),
      mkResult({ status: 'error',   totalTime: 30, responseTime: 20, timestamp: new Date('2023-01-01T00:00:02Z'), endpoint: { ...baseEndpoint, category: 'users' } }),
      mkResult({ status: 'success', totalTime: 20, responseTime: 10, timestamp: new Date('2023-01-01T00:00:03Z'), endpoint: { ...baseEndpoint, category: 'auth' } }),
    ];
    const stats = calculateStatistics(results);
    expect(stats.totalRequests).toBe(3);
    expect(stats.successRate).toBeCloseTo((2 / 3) * 100);
    expect(stats.errorRate).toBeCloseTo((1 / 3) * 100);
    expect(stats.minResponseTime).toBe(10);
    expect(stats.maxResponseTime).toBe(40);
    expect(stats.averageResponseTime).toBeCloseTo((40 + 20 + 10) / 3);
    // Session duration: from t=0 to t=3s => 3s, throughput = 3 / 3 = 1 rps
    expect(stats.throughput).toBeCloseTo(1, 5);
    expect(stats.categoriesStats.users.total).toBe(2);
    expect(stats.categoriesStats.users.successful).toBe(1);
    expect(stats.categoriesStats.users.failed).toBe(1);
    expect(stats.categoriesStats.users.averageTime).toBeCloseTo((50 + 30) / 2);
    expect(stats.categoriesStats.auth.total).toBe(1);
    expect(stats.categoriesStats.auth.successful).toBe(1);
    expect(stats.categoriesStats.auth.failed).toBe(0);
  });
});

describe('helpers: resume data (save/load/clear)', () => {
  const sessionId = 'sess-123';
  const now = new Date('2024-01-01T00:00:00Z');

  beforeEach(() => {
    // @ts-ignore jsdom provides localStorage; ensure clean state
    localStorage.clear();
    jest.spyOn(global, 'Date').mockImplementation(((...args: any[]) => {
      return args.length ? new (Date as any)(...args) : new (Date as any)(now) as any;
    }) as any);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('saves and loads resume data', () => {
    const partialResults: TestResult[] = [];
    const config = { threads: 4 };

    saveResumeData(sessionId, 7, config as any, partialResults);
    const loaded = loadResumeData(sessionId);
    expect(loaded).not.toBeNull();
    expect(loaded!.sessionId).toBe(sessionId);
    expect(loaded!.lastCompletedIndex).toBe(7);
    expect(loaded!.config).toEqual(config);
    expect(loaded!.partialResults).toEqual(partialResults);
    expect(loaded!.timestamp).toBeInstanceOf(Date);
  });

  it('loads null when no session id present', () => {
    expect(loadResumeData()).toBeNull();
  });

  it('clears resume data and last_session_id appropriately', () => {
    saveResumeData(sessionId, 0, {}, []);
    expect(loadResumeData(sessionId)).not.toBeNull();
    clearResumeData(sessionId);
    expect(loadResumeData(sessionId)).toBeNull();
    // last_session_id should be removed if pointing to the same
    expect(localStorage.getItem('last_session_id')).toBeNull();
  });
});

describe('helpers: exportResults (JSON) and exportResultsCSV', () => {
  let createObjectURLSpy: jest.SpyInstance;
  let revokeObjectURLSpy: jest.SpyInstance;
  let appendChildSpy: jest.SpyInstance;
  let removeChildSpy: jest.SpyInstance;
  let clickSpy: jest.SpyInstance;

  beforeEach(() => {
    createObjectURLSpy = jest.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock');
    revokeObjectURLSpy = jest.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    appendChildSpy = jest.spyOn(document.body, 'appendChild');
    removeChildSpy = jest.spyOn(document.body, 'removeChild');
    clickSpy = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  const session: TestSession = {
    id: 'session-1',
    name: 'Sample',
    startedAt: new Date('2024-05-01T00:00:00Z'),
    results: [
      {
        endpoint: { name: 'Ping', method: 'GET', path: '/ping', category: 'health' },
        status: 'success',
        requestTime: 5,
        responseTime: 10,
        totalTime: 15,
        timestamp: new Date('2024-05-01T00:00:01Z'),
      },
    ],
  };

  it('exportResults creates a downloadable JSON blob and revokes it', () => {
    exportResults(session as any);
    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(appendChildSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock');
  });

  it('exportResultsCSV creates a CSV blob and triggers download', () => {
    exportResultsCSV(session.results as any);
    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(appendChildSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
  });
});

describe('helpers: deepClone', () => {
  it('clones primitives as-is', () => {
    expect(deepClone(5)).toBe(5);
    expect(deepClone('a')).toBe('a');
    expect(deepClone(true)).toBe(true);
    expect(deepClone(null as any)).toBeNull();
  });

  it('clones Date instances', () => {
    const d = new Date();
    const c = deepClone(d);
    expect(c).not.toBe(d);
    expect(c.getTime()).toBe(d.getTime());
  });

  it('clones arrays deeply', () => {
    const arr = [{ a: 1 }, { b: [2, 3] }];
    const cloned = deepClone(arr);
    expect(cloned).not.toBe(arr);
    expect(cloned).toEqual(arr);
    (cloned[0] as any).a = 9;
    expect((arr[0] as any).a).toBe(1);
  });

  it('clones objects deeply', () => {
    const obj = { x: { y: [1, { z: 3 }] } };
    const cloned = deepClone(obj);
    expect(cloned).toEqual(obj);
    (cloned.x.y[1] as any).z = 4;
    expect((obj.x.y[1] as any).z).toBe(3);
  });
});

describe('helpers: debounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('debounces function calls until wait elapses', () => {
    const fn = jest.fn();
    const deb = debounce(fn, 200);
    deb(1);
    deb(2);
    expect(fn).not.toHaveBeenCalled();
    jest.advanceTimersByTime(199);
    expect(fn).not.toHaveBeenCalled();
    jest.advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledTimes(1);
    // Last call args should be applied
    expect(fn).toHaveBeenLastCalledWith(2);
  });
});

describe('helpers: throttle', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('invokes immediately and then throttles within the limit', () => {
    const fn = jest.fn();
    const thr = throttle(fn, 100);
    thr('a'); // immediate
    thr('b'); // throttled
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('a');
    jest.advanceTimersByTime(100);
    thr('c'); // allowed again
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith('c');
  });
});

describe('helpers: getStatusColor', () => {
  it('returns correct colors for known statuses and default', () => {
    expect(getStatusColor('success')).toBe('#10b981');
    expect(getStatusColor('error')).toBe('#ef4444');
    expect(getStatusColor('timeout')).toBe('#f59e0b');
    expect(getStatusColor('pending')).toBe('#6b7280');
    expect(getStatusColor('unknown')).toBe('#6b7280');
  });
});

describe('helpers: getAccuracyColor', () => {
  it('returns color bands by thresholds', () => {
    expect(getAccuracyColor(95)).toBe('#10b981');
    expect(getAccuracyColor(75)).toBe('#f59e0b');
    expect(getAccuracyColor(55)).toBe('#f97316');
    expect(getAccuracyColor(10)).toBe('#ef4444');
  });
});

describe('helpers: isValidUrl', () => {
  it('validates correct and incorrect URLs', () => {
    expect(isValidUrl('https://example.com')).toBe(true);
    expect(isValidUrl('http://localhost:3000/path')).toBe(true);
    expect(isValidUrl('not a url')).toBe(false);
    expect(isValidUrl('ftp://example.com')).toBe(true);
  });
});

describe('helpers: generateTestPayload', () => {
  it('returns undefined when no payload schema present', () => {
    expect(generateTestPayload({} as any)).toBeUndefined();
  });
  it('generates payload with various types including file Blob', () => {
    const endpoint = {
      payload: {
        name: 'string',
        age: 'number',
        active: 'boolean',
        tags: 'array',
        meta: 'object',
        file: 'file',
      },
    };
    const payload: any = generateTestPayload(endpoint);
    expect(typeof payload.name).toBe('string');
    expect(typeof payload.age).toBe('number');
    expect(typeof payload.active).toBe('boolean');
    expect(Array.isArray(payload.tags)).toBe(true);
    expect(typeof payload.meta).toBe('object');
    expect(payload.file).toBeInstanceOf(Blob);
  });
});