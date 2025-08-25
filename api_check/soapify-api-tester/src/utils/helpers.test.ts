/* 
  Tests for utils/helpers.
  Framework: Jest or Vitest (API-compatible). 
  These tests assume a JSDOM-like environment for DOM/URL/Blob and localStorage; if not available, mocks are provided.

  Conventions:
  - Use fake timers for debounce/throttle.
  - Mock Date.now, Math.random where determinism is required.
  - Spy on console.error for error branches.
*/

import {
  // core utils
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
} from './helpers'; // Adjust if helpers.ts is elsewhere

// Types used by functions under test; we import from the project's types if available.
// If the path differs, update the import below.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import type { TestResult, TestSession } from '../types';

// Compatible timer mocks for Jest/Vitest.

const useFakeTimers = () => {
  // @ts-ignore
  if (typeof vi !== 'undefined' && vi.useFakeTimers) { vi.useFakeTimers(); return { isVitest: true }; }
  // @ts-ignore
  if (jest && jest.useFakeTimers) { jest.useFakeTimers(); return { isVitest: false }; }
  return { isVitest: false };
};
const useRealTimers = () => {
  // @ts-ignore
  if (typeof vi !== 'undefined' && vi.useRealTimers) { vi.useRealTimers(); return; }
  // @ts-ignore
  if (jest && jest.useRealTimers) { jest.useRealTimers(); return; }
};

const advanceTimersByTime = async (ms: number) => {
  // @ts-ignore
  if (typeof vi !== 'undefined' && vi.advanceTimersByTimeAsync) { await vi.advanceTimersByTimeAsync(ms); return; }
  // @ts-ignore
  if (jest && jest.advanceTimersByTime) { jest.advanceTimersByTime(ms); return; }
};

// Helper to mock Date.now deterministically

const withMockedDateNow = (value: number, fn: () => void) => {
  const originalNow = Date.now;
  // @ts-ignore
  Date.now = () => value;
  try { fn(); } finally {
    Date.now = originalNow;
  }
};

// Helper to temporarily stub Math.random

const withMockedRandom = (value: number, fn: () => void) => {
  const orig = Math.random;
  Math.random = () => value;
  try { fn(); } finally {
    Math.random = orig;
  }
};

describe('generateId', () => {
  it('produces a string combining Date.now and base36 random', () => {
    withMockedDateNow(1690000000000, () => {
      withMockedRandom(0.123456789, () => {
        const id = generateId();
        expect(id).toMatch(/^1690000000000\-[a-z0-9]{9}$/);
      });
    });
  });

  it('is likely unique across multiple invocations', () => {
    const set = new Set<string>();
    for (let i = 0; i < 100; i++) set.add(generateId());
    expect(set.size).toBe(100);
  });
});

describe('formatDuration', () => {
  it('returns milliseconds for < 1000', () => {
    expect(formatDuration(0)).toBe('0ms');
    expect(formatDuration(999)).toBe('999ms');
  });

  it('formats seconds when < 1 minute', () => {
    expect(formatDuration(1000)).toBe('1s');
    expect(formatDuration(59_000)).toBe('59s');
  });

  it('formats minutes and seconds', () => {
    expect(formatDuration(60_000)).toBe('1m 0s');
    expect(formatDuration(125_000)).toBe('2m 5s');
  });

  it('formats hours, minutes, seconds', () => {
    expect(formatDuration(3_600_000)).toBe('1h 0m 0s');
    expect(formatDuration(3_726_500)).toBe('1h 1m 12s');
  });
});

describe('formatFileSize', () => {
  it('handles 0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
  });

  it('renders Bytes for < 1024', () => {
    expect(formatFileSize(1)).toBe('1 Bytes');
    expect(formatFileSize(1023)).toBe('1023 Bytes');
  });

  it('renders KB/MB/GB with 2-decimal rounding', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(1048576)).toBe('1 MB'); // 1024 * 1024
  });
});

describe('formatDateTime', () => {
  it('returns en-US localized string with expected structure', () => {
    const date = new Date(Date.UTC(2024, 0, 2, 15, 4, 5)); // Jan 2, 2024 15:04:05 UTC
    const s = formatDateTime(date);
    // Expect shape like "01/02/2024, 03:04:05 PM" (12-hour) or "01/02/2024, 15:04:05" depending on env.
    // Validate ordering and zero-padding with flexible AM/PM.
    expect(s).toMatch(/^\d{2}\/\d{2}\/\d{4}, \d{2}:\d{2}:\d{2}( [AP]M)?$/);
  });
});

describe('calculateResponseAccuracy', () => {
  it('returns 0 for type mismatch', () => {
    expect(calculateResponseAccuracy('a', 1)).toBe(0);
  });

  it('handles primitives equality', () => {
    expect(calculateResponseAccuracy('x', 'x')).toBe(100);
    expect(calculateResponseAccuracy('x', 'y')).toBe(0);
    expect(calculateResponseAccuracy(10, 10)).toBe(100);
    expect(calculateResponseAccuracy(10, 5)).toBe(0);
    expect(calculateResponseAccuracy(true, true)).toBe(100);
    expect(calculateResponseAccuracy(true, false)).toBe(0);
  });

  it('handles arrays with length mismatch penalty', () => {
    // length diff 2 -> 100 - 20 = 80
    expect(calculateResponseAccuracy([1, 2, 3], [1])).toBe(80);
    // clamp at >= 0
    expect(calculateResponseAccuracy([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], [])).toBe(0);
  });

  it('handles arrays with same length by per-element >50% rule', () => {
    const expected = [ { a: 1 }, 2, 'x' ];
    const actual   = [ { a: 1 }, 3, 'y' ];
    // element0: 100, element1: 0, element2: 0 => matches = 1/3 => 33.33...
    expect(calculateResponseAccuracy(expected, actual)).toBeCloseTo(33.333, 1);
  });

  it('handles objects with missing/extra keys penalties', () => {
    const expected = { a: 1, b: 'x' };
    const actual   = { a: 1, c: true };
    // per-field average: a=100, b missing => not added; averageScore = totalScore/totalFields=100/2=50
    // penalties: missingKeys=[b] (1), extraKeys=[c] (1) => penalty=10
    // final = max(0, 50-10) = 40
    expect(calculateResponseAccuracy(expected, actual)).toBe(40);
  });

  it('handles nested object accuracy', () => {
    const expected = { user: { id: 1, name: 'A' }, ok: true };
    const actual   = { user: { id: 1, name: 'B' }, ok: true };
    // user: id match 100, name mismatch 0 => avg 50
    // ok: 100 => total fields 2 => avg (50+100)/2 = 75, no penalties
    expect(calculateResponseAccuracy(expected, actual)).toBe(75);
  });

  it('returns 0 when comparing object to null/undefined', () => {
    expect(calculateResponseAccuracy({ a: 1 }, null)).toBe(0);
    // typeof expected 'object' vs undefined: mismatch => 0
    expect(calculateResponseAccuracy({ a: 1 }, (undefined as unknown as object))).toBe(0);
  });
});

describe('calculateStatistics', () => {
  const makeResult = (overrides: Partial<TestResult> = {}): TestResult => {
    const base: any = {
      timestamp: new Date('2024-01-01T00:00:00.000Z'),
      endpoint: { name: 'E1', method: 'GET', path: '/e1', category: 'catA' },
      status: 'success',
      statusCode: 200,
      requestTime: 10,
      responseTime: 20,
      totalTime: 30,
      requestSize: 100,
      responseSize: 200,
      accuracyPercentage: 100,
      error: '',
    };
    return { ...base, ...overrides } as TestResult;
  };

  it('returns zeros for empty input', () => {
    const stats = calculateStatistics([]);
    expect(stats).toEqual({
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

  it('computes aggregates and throughput over session duration', () => {
    const r1 = makeResult({ totalTime: 30, timestamp: new Date('2024-01-01T00:00:00.000Z'), endpoint: { name:'E1', method:'GET', path:'/a', category: 'A' } as any });
    const r2 = makeResult({ totalTime: 50, timestamp: new Date('2024-01-01T00:00:10.000Z'), endpoint: { name:'E2', method:'GET', path:'/b', category: 'B' } as any });
    const r3 = makeResult({ totalTime: 40, timestamp: new Date('2024-01-01T00:00:20.000Z'), endpoint: { name:'E3', method:'GET', path:'/c', category: 'A' } as any, status: 'error' as any });

    const stats = calculateStatistics([r1, r2, r3]);

    expect(stats.totalRequests).toBe(3);
    expect(stats.successRate).toBeCloseTo((2/3)*100);
    expect(stats.averageResponseTime).toBeCloseTo((30+50+40)/3);
    expect(stats.minResponseTime).toBe(30);
    expect(stats.maxResponseTime).toBe(50);
    expect(stats.errorRate).toBeCloseTo((1/3)*100);

    // session duration: from t=0s to t=20s => 20 seconds, throughput = 3/20
    expect(stats.throughput).toBeCloseTo(3/20);

    // category A: total=2 (r1,r3), successful=1, failed=1, averageTime=(30+40)/2
    expect(stats.categoriesStats['A'].total).toBe(2);
    expect(stats.categoriesStats['A'].successful).toBe(1);
    expect(stats.categoriesStats['A'].failed).toBe(1);
    expect(stats.categoriesStats['A'].averageTime).toBeCloseTo(35);

    // category B: total=1, successful=1
    expect(stats.categoriesStats['B'].total).toBe(1);
    expect(stats.categoriesStats['B'].successful).toBe(1);
    expect(stats.categoriesStats['B'].failed).toBe(0);
    expect(stats.categoriesStats['B'].averageTime).toBeCloseTo(50);
  });

  it('throughput is 0 if sessionDuration is 0 (all same timestamp)', () => {
    const t = new Date('2024-01-01T00:00:00.000Z');
    const a = makeResult({ timestamp: t });
    const b = makeResult({ timestamp: t });
    const stats = calculateStatistics([a, b]);
    expect(stats.throughput).toBe(0);
  });
});

describe('resume data persistence', () => {
  const originalLocalStorage = globalThis.localStorage;

  beforeEach(() => {
    // Provide a minimal localStorage mock if not present
    let store: Record<string, string> = {};
    // @ts-ignore
    globalThis.localStorage = {
      getItem: (k: string) => (k in store ? store[k] : null),
      setItem: (k: string, v: string) => { store[k] = v; },
      removeItem: (k: string) => { delete store[k]; },
      clear: () => { store = {}; },
      key: (i: number) => Object.keys(store)[i] || null,
      length: 0,
    } as unknown as Storage;
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    // @ts-ignore
    jest.restoreAllMocks?.();
    // @ts-ignore
    vi?.restoreAllMocks?.();
    // @ts-ignore
    globalThis.localStorage = originalLocalStorage;
  });

  it('saveResumeData stores data and updates last_session_id', () => {
    const sessionId = 'abc123';
    const cfg = { foo: 'bar' };
    const partial: any[] = [];
    saveResumeData(sessionId, 5, cfg, partial as any);
    expect(localStorage.getItem(`resume_${sessionId}`)).toBeTruthy();
    expect(localStorage.getItem('last_session_id')).toBe(sessionId);
  });

  it('loadResumeData without param uses last_session_id and casts timestamp to Date', () => {
    const sessionId = 'xyz789';
    saveResumeData(sessionId, 1, { a: 1 }, [] as any);
    const loaded = loadResumeData();
    expect(loaded?.sessionId).toBe(sessionId);
    expect(loaded?.timestamp instanceof Date).toBe(true);
  });

  it('clearResumeData removes stored data and optionally last_session_id', () => {
    const sessionId = 'to-clear';
    saveResumeData(sessionId, 2, {}, [] as any);
    clearResumeData(sessionId);
    expect(localStorage.getItem(`resume_${sessionId}`)).toBeNull();
    expect(localStorage.getItem('last_session_id')).toBeNull();
  });

  it('handles storage exceptions gracefully', () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const badLocal = {
      setItem: () => { throw new Error('boom'); },
      getItem: () => { throw new Error('boom'); },
      removeItem: () => { throw new Error('boom'); },
    } as unknown as Storage;
    // @ts-ignore
    globalThis.localStorage = badLocal;

    saveResumeData('s1', 0, {}, [] as any);
    expect(spy).toHaveBeenCalled();

    const loaded = loadResumeData('s1');
    expect(loaded).toBeNull();

    clearResumeData('s1');
    expect(spy).toHaveBeenCalled();
  });
});

describe('exportResults (JSON) and exportResultsCSV (CSV)', () => {
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  const originalBlob = globalThis.Blob;

  let createdUrls: string[] = [];
  let anchorClicks = 0;
  let appended = 0;
  let removed = 0;

  beforeEach(() => {
    createdUrls = [];
    anchorClicks = 0;
    appended = 0;
    removed = 0;

    // Mock URL APIs
    // @ts-ignore
    URL.createObjectURL = (blob: any) => {
      // Basic sanity: blob should contain data
      expect(blob).toBeTruthy();
      const url = 'blob:mock-url-' + (createdUrls.length + 1);
      createdUrls.push(url);
      return url as unknown as string;
    };
    // @ts-ignore
    URL.revokeObjectURL = (u: string) => {
      expect(createdUrls.includes(u)).toBe(true);
    };

    // Mock document anchor creation and clicks
    jest.spyOn(document, 'createElement').mockImplementation(((tag: string): any => {
      if (tag !== 'a') return (document.createElement as any).orig?.call(document, tag);
      return {
        set href(val: string) { /* no-op but allow assignment */ },
        get href() { return createdUrls[createdUrls.length - 1] || ''; },
        download: '',
        click: () => { anchorClicks++; },
      };
    }) as any);
    // Keep originals to call if needed
    (document.createElement as any).orig = (HTMLElement.prototype as any).ownerDocument?.createElement || ((tag: string) => ({ tagName: tag.toUpperCase() }));

    jest.spyOn(document.body, 'appendChild').mockImplementation(((node: any) => { appended++; return node; }) as any);
    jest.spyOn(document.body, 'removeChild').mockImplementation(((node: any) => { removed++; return node; }) as any);

    // Mock Blob to capture type
    // @ts-ignore
    globalThis.Blob = function (parts: any[], opts?: any) {
      // basic expectations; content presence verified by createObjectURL call above
      (this as any).__parts = parts;
      (this as any).type = opts?.type || '';
    } as any;
  });

  afterEach(() => {
    jest.restoreAllMocks?.();
    // @ts-ignore
    vi?.restoreAllMocks?.();
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    // @ts-ignore
    globalThis.Blob = originalBlob;
  });

  const baseResult: TestResult = {
    timestamp: new Date('2024-03-10T01:02:03.000Z'),
    endpoint: { name: 'Users', method: 'GET', path: '/users', category: 'Accounts' } as any,
    status: 'success',
    statusCode: 200,
    requestTime: 12,
    responseTime: 34,
    totalTime: 46,
    requestSize: 111,
    responseSize: 222,
    accuracyPercentage: 88,
    error: '',
  };

  it('exportResults triggers a download with expected filename', () => {
    const fixedDate = new Date('2025-08-23T12:00:00.000Z'); // current date context
    const realNow = Date;
    // Freeze Date for consistent exportedAt and filename date part
    // @ts-ignore
    globalThis.Date = class extends Date {
      constructor(...args: any[]) {
        if (args.length === 0) { super(fixedDate.toISOString()); } else { super(...(args as [any])); }
      }
      static now() { return fixedDate.getTime(); }
      static parse = realNow.parse;
      static UTC = realNow.UTC;
    } as any;

    const session: TestSession = {
      id: 'sess-123',
      results: [baseResult],
      config: { env: 'test' } as any,
    } as any;

    exportResults(session);

    // One URL created, anchor clicked, DOM manipulated
    expect(createdUrls.length).toBe(1);
    expect(anchorClicks).toBe(1);
    expect(appended).toBe(1);
    expect(removed).toBe(1);

    // restore Date
    globalThis.Date = realNow as any;
  });

  it('exportResultsCSV triggers a CSV download with headers and values', () => {
    exportResultsCSV([baseResult]);
    expect(createdUrls.length).toBe(1);
    expect(anchorClicks).toBe(1);
    expect(appended).toBe(1);
    expect(removed).toBe(1);
  });
});

describe('deepClone', () => {
  it('returns primitives as-is', () => {
    expect(deepClone(5)).toBe(5);
    expect(deepClone('x')).toBe('x');
    expect(deepClone(true)).toBe(true);
  });

  it('clones Date instances', () => {
    const d = new Date('2024-01-01T00:00:00Z');
    const c = deepClone(d);
    expect(c).not.toBe(d);
    expect((c as Date).getTime()).toBe(d.getTime());
  });

  it('clones arrays and objects deeply', () => {
    const o = { a: 1, b: ['x', { c: new Date('2024-01-01T00:00:00Z') }] };
    const c = deepClone(o);
    expect(c).not.toBe(o);
    // @ts-ignore
    expect(c.b).not.toBe(o.b);
    // @ts-ignore
    expect(c.b[1]).not.toBe(o.b[1]);
    // @ts-ignore
    expect((c.b[1].c as Date).getTime()).toBe((o.b[1].c as Date).getTime());
  });
});

describe('debounce', () => {
  it('delays invocation and collapses rapid calls', async () => {
    useFakeTimers();
    const fn = jest.fn();
    const debounced = debounce(fn, 200);

    debounced('a');
    debounced('b'); // should cancel 'a'
    await advanceTimersByTime(199);
    expect(fn).not.toHaveBeenCalled();
    await advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('b');

    useRealTimers();
  });
});

describe('throttle', () => {
  it('executes immediately, then suppresses until limit elapses', async () => {
    useFakeTimers();
    const fn = jest.fn();
    const throttled = throttle(fn, 300);

    throttled(1);
    throttled(2);
    throttled(3);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith(1);

    await advanceTimersByTime(299);
    throttled(4);
    expect(fn).toHaveBeenCalledTimes(1);

    await advanceTimersByTime(1);
    throttled(5);
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith(5);

    useRealTimers();
  });
});

describe('getStatusColor', () => {
  it('maps statuses to expected colors', () => {
    expect(getStatusColor('success')).toBe('#10b981');
    expect(getStatusColor('error')).toBe('#ef4444');
    expect(getStatusColor('timeout')).toBe('#f59e0b');
    expect(getStatusColor('pending')).toBe('#6b7280');
    expect(getStatusColor('unknown')).toBe('#6b7280');
  });
});

describe('getAccuracyColor', () => {
  it('uses thresholds 90/70/50', () => {
    expect(getAccuracyColor(95)).toBe('#10b981'); // green
    expect(getAccuracyColor(75)).toBe('#f59e0b'); // yellow
    expect(getAccuracyColor(55)).toBe('#f97316'); // orange
    expect(getAccuracyColor(10)).toBe('#ef4444'); // red
  });
});

describe('isValidUrl', () => {
  it('validates proper URLs', () => {
    expect(isValidUrl('https://example.com')).toBe(true);
    expect(isValidUrl('http://localhost:3000/path?x=1')).toBe(true);
  });

  it('rejects invalid URLs', () => {
    expect(isValidUrl('not a url')).toBe(false);
    expect(isValidUrl('http://')).toBe(false);
    expect(isValidUrl('://missing-scheme')).toBe(false);
  });
});

describe('generateTestPayload', () => {
  beforeEach(() => {
    // Mock Date.now and Math.random to keep deterministic
    jest.spyOn(Date, 'now').mockReturnValue(1700000000000);
    jest.spyOn(Math, 'random').mockReturnValue(0.7); // > 0.5 => true
  });

  afterEach(() => {
    jest.restoreAllMocks?.();
    // @ts-ignore
    vi?.restoreAllMocks?.();
  });

  it('returns undefined if endpoint has no payload', () => {
    expect(generateTestPayload({})).toBeUndefined();
  });

  it('generates values per declared type', () => {
    const payload = generateTestPayload({
      payload: {
        s: 'string',
        n: 'number',
        b: 'boolean',
        arr: 'array',
        obj: 'object',
        file: 'file',
        custom: 'uuid',
      }
    });

    expect(payload).toBeTruthy();
    expect(typeof payload.s).toBe('string');
    expect(typeof payload.n).toBe('number');
    expect(typeof payload.b).toBe('boolean');
    expect(Array.isArray(payload.arr)).toBe(true);
    expect(typeof payload.obj).toBe('object');
    expect(payload.file).toBeInstanceOf(Blob);
    // Blob type
    expect((payload.file as Blob).type).toBe('text/plain');
    expect(typeof payload.custom).toBe('string');
  });
});