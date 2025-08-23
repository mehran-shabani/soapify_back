/**
 * Test suite for helpers utilities.
 *
 * Testing library/framework:
 * - This test suite is designed to work with the repository's existing test runner.
 *   If the project uses Jest (common: jest, ts-jest), the global jest APIs will be used.
 *   If the project uses Vitest, we seamlessly switch to vi APIs by aliasing.
 *
 * Conventions:
 * - File co-located under src/utils with *.test.ts naming, matching common patterns.
 * - Uses jsdom-like environment for DOM-dependent helpers (Blob, URL, document, localStorage).
 */

 /* eslint-disable @typescript-eslint/no-explicit-any */

 // Support both Jest and Vitest by aliasing globals where necessary
 // (Prefer existing project's framework; these fallbacks prevent reference errors.)
 const _isVitest = typeof vi !== 'undefined';
 const _isJest = typeof jest !== 'undefined';

 const testFn = (_isVitest ? (vi as any) : (_isJest ? (jest as any) : undefined));
 if (!testFn) {
   // Soft-guard: tests will likely be executed under Jest or Vitest;
   // this avoids crashes if executed in a different runner.
   // @ts-ignore
   globalThis.jest = globalThis.jest || {};
 }

 const useFakeTimers = (clock: 'modern' | 'legacy' = 'modern') => {
   if (_isVitest) vi.useFakeTimers();
   else if (_isJest) jest.useFakeTimers(clock);
 };

 const setSystemTime = (d: Date) => {
   if (_isVitest) vi.setSystemTime(d);
   else if (_isJest && (jest as any).setSystemTime) (jest as any).setSystemTime(d);
 };

 const advanceTimersByTime = (ms: number) => {
   if (_isVitest) vi.advanceTimersByTime(ms);
   else if (_isJest) jest.advanceTimersByTime(ms);
 };

 const runAllTimers = () => {
   if (_isVitest) vi.runAllTimers();
   else if (_isJest) jest.runAllTimers();
 };

 const spyOn = (obj: any, method: string) => {
   if (_isVitest) return vi.spyOn(obj, method as any);
   if (_isJest) return jest.spyOn(obj, method as any);
   throw new Error('No spy API available');
 };

 const fn = () => (_isVitest ? vi.fn() : _isJest ? jest.fn() : () => {});

 // Import the helpers under test
 import * as Helpers from './helpers';

 type TestResult = {
   endpoint: { name: string; method: string; path: string; category: string };
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
   startedAt: Date;
   completedAt?: Date;
   config: any;
   results: TestResult[];
 };

 describe('generateId', () => {
   it('generates unique ids and matches expected pattern "<timestamp>-<random>"', () => {
     // Fix time and random to assert determinism on format while keeping uniqueness
     const fixedNow = 1735689600000; // 2025-01-01T00:00:00.000Z (example)
     const origNow = Date.now;
     // @ts-ignore
     Date.now = () => fixedNow;

     const origRandom = Math.random;
     Math.random = () => 0.123456789; // toString(36).substr(2,9) should be deterministic

     const id = Helpers.generateId();
     expect(id).toMatch(/^1735689600000-[a-z0-9]{9}$/);

     // Restore random to generate a different id for uniqueness check
     Math.random = origRandom;
     const id2 = Helpers.generateId();

     // cleanup
     // @ts-ignore
     Date.now = origNow;

     expect(id).not.toEqual(id2);
   });
 });

 describe('formatDuration', () => {
   it('formats sub-second durations in ms', () => {
     expect(Helpers.formatDuration(0)).toBe('0ms');
     expect(Helpers.formatDuration(999)).toBe('999ms');
   });

   it('formats seconds correctly', () => {
     expect(Helpers.formatDuration(1000)).toBe('1s');
     expect(Helpers.formatDuration(59_000)).toBe('59s');
   });

   it('formats minutes and seconds', () => {
     expect(Helpers.formatDuration(60_000)).toBe('1m 0s');
     expect(Helpers.formatDuration(61_000)).toBe('1m 1s');
     expect(Helpers.formatDuration(125_000)).toBe('2m 5s');
   });

   it('formats hours, minutes, and seconds', () => {
     const ms = (1 * 3600 + 1 * 60 + 5) * 1000; // 1h 1m 5s
     expect(Helpers.formatDuration(ms)).toBe('1h 1m 5s');
   });
 });

 describe('formatFileSize', () => {
   it('handles zero bytes', () => {
     expect(Helpers.formatFileSize(0)).toBe('0 Bytes');
   });

   it('handles bytes under 1KB', () => {
     expect(Helpers.formatFileSize(500)).toBe('500 Bytes');
   });

   it('handles KB and MB rounding to 2 decimals (via Math.round over 100)', () => {
     expect(Helpers.formatFileSize(1536)).toBe('1.5 KB');      // 1.5 KB
     expect(Helpers.formatFileSize(1048576)).toBe('1 MB');     // 1 MB
     expect(Helpers.formatFileSize(1073741824)).toBe('1 GB');  // 1 GB
   });
 });

 describe('formatDateTime', () => {
   const originalTZ = process.env.TZ;

   beforeAll(() => {
     process.env.TZ = 'UTC';
   });

   afterAll(() => {
     process.env.TZ = originalTZ;
   });

   it('formats date consistently in en-US with 2-digit parts', () => {
     const d = new Date('2023-01-02T03:04:05Z');
     const formatted = Helpers.formatDateTime(d);
     // Match "01/02/2023, 03:04:05 AM" or without AM/PM depending on env; ensure core parts present
     expect(formatted).toContain('01/02/2023');
     expect(formatted).toMatch(/03:04:05/);
   });
 });

 describe('calculateResponseAccuracy', () => {
   it('returns 0 for different types', () => {
     expect(Helpers.calculateResponseAccuracy('1', 1)).toBe(0);
     expect(Helpers.calculateResponseAccuracy({}, [])).toBe(0);
   });

   it('handles primitive equality checks', () => {
     expect(Helpers.calculateResponseAccuracy('abc', 'abc')).toBe(100);
     expect(Helpers.calculateResponseAccuracy('abc', 'def')).toBe(0);
     expect(Helpers.calculateResponseAccuracy(42, 42)).toBe(100);
     expect(Helpers.calculateResponseAccuracy(true, true)).toBe(100);
     expect(Helpers.calculateResponseAccuracy(false, true)).toBe(0);
   });

   it('handles arrays: length mismatch applies penalty rule', () => {
     expect(Helpers.calculateResponseAccuracy([1,2,3], [1,2])).toBe(90);
     expect(Helpers.calculateResponseAccuracy([1], [])).toBe(90);
   });

   it('handles arrays: per-item >50 accuracy threshold counts as match', () => {
     // 2 matches out of 3 => 66.666...
     expect(Helpers.calculateResponseAccuracy([1,2,3], [1,2,999])).toBeCloseTo((2/3)*100, 6);
   });

   it('handles objects: missing/extra keys penalize 5 each; scoring uses field averages', () => {
     const expected = { a: 1, b: 'x' };
     const actualPerfect = { a: 1, b: 'x' };
     const actualWithExtra = { a: 1, b: 'x', c: 3 };
     const actualWithMissing = { a: 1 };

     expect(Helpers.calculateResponseAccuracy(expected, actualPerfect)).toBe(100);
     expect(Helpers.calculateResponseAccuracy(expected, actualWithExtra)).toBe(95); // 100 avg - 5 extra
     // Average: a=100, b missing so not included in score loop; totalFields=2 -> totalScore=100 -> avg=50; penalty=5 (1 missing)
     expect(Helpers.calculateResponseAccuracy(expected, actualWithMissing)).toBe(Math.max(0, 50 - 5));
   });

   it('returns 0 for null actual vs object expected', () => {
     expect(Helpers.calculateResponseAccuracy({ a: 1 }, null as any)).toBe(0);
   });
 });

 describe('calculateStatistics', () => {
   const baseTs = new Date('2025-01-01T00:00:00Z');

   const mkResult = (over: Partial<TestResult>): TestResult => ({
     endpoint: { name: 'E', method: 'GET', path: '/e', category: 'cat' },
     status: 'success',
     requestTime: 10,
     responseTime: 20,
     totalTime: 30,
     timestamp: baseTs,
     ...over,
   });

   it('returns zeros for empty results', () => {
     const stats = Helpers.calculateStatistics([]);
     expect(stats).toEqual({
       totalRequests: 0,
       successRate: 0,
       averageResponseTime: 0,
       minResponseTime: 0,
       maxResponseTime: 0,
       errorRate: 0,
       throughput: 0,
       categoriesStats: {}
     });
   });

   it('computes aggregates, error rate, throughput, and category averages', () => {
     const results: TestResult[] = [
       mkResult({ totalTime: 30, requestTime: 10, responseTime: 20, status: 'success', timestamp: new Date(baseTs) , endpoint: {name:'E1', method:'GET', path:'/a', category:'A'} }),
       mkResult({ totalTime: 50, requestTime: 15, responseTime: 35, status: 'error',  timestamp: new Date(baseTs.getTime() + 5_000), endpoint: {name:'E2', method:'POST', path:'/b', category:'B'} }),
       mkResult({ totalTime: 40, requestTime: 20, responseTime: 20, status: 'success', timestamp: new Date(baseTs.getTime() + 10_000), endpoint: {name:'E3', method:'GET', path:'/c', category:'A'} }),
     ];
     const stats = Helpers.calculateStatistics(results);

     expect(stats.totalRequests).toBe(3);
     expect(stats.successRate).toBeCloseTo((2/3)*100);
     expect(stats.errorRate).toBeCloseTo((1/3)*100);

     expect(stats.averageResponseTime).toBeCloseTo((30+50+40)/3);
     expect(stats.minResponseTime).toBe(30);
     expect(stats.maxResponseTime).toBe(50);

     // Duration = 10 seconds from first to last -> throughput = 3/10
     expect(stats.throughput).toBeCloseTo(0.3, 5);

     expect(Object.keys(stats.categoriesStats)).toEqual(expect.arrayContaining(['A','B']));
     expect(stats.categoriesStats['A'].total).toBe(2);
     expect(stats.categoriesStats['A'].successful).toBe(2);
     expect(stats.categoriesStats['A'].failed).toBe(0);
     expect(stats.categoriesStats['A'].averageTime).toBeCloseTo((30+40)/2);

     expect(stats.categoriesStats['B'].total).toBe(1);
     expect(stats.categoriesStats['B'].successful).toBe(0);
     expect(stats.categoriesStats['B'].failed).toBe(1);
     expect(stats.categoriesStats['B'].averageTime).toBeCloseTo(50);
   });

   it('yields throughput 0 when sessionDuration is 0 (all timestamps equal)', () => {
     const results: TestResult[] = [
       mkResult({ totalTime: 10, timestamp: new Date(baseTs) }),
       mkResult({ totalTime: 20, timestamp: new Date(baseTs) }),
     ];
     const stats = Helpers.calculateStatistics(results);
     expect(stats.throughput).toBe(0);
   });
 });

 describe('resume data helpers (save/load/clear)', () => {
   const sessionId = 'sess-123';

   beforeEach(() => {
     // Ensure jsdom-style localStorage is present; if not, provide a minimal mock
     if (typeof localStorage === 'undefined' || !localStorage) {
       // @ts-ignore
       global.localStorage = (function () {
         let store: Record<string, string> = {};
         return {
           getItem: (k: string) => (k in store ? store[k] : null),
           setItem: (k: string, v: string) => { store[k] = String(v); },
           removeItem: (k: string) => { delete store[k]; },
           clear: () => { store = {}; }
         };
       })();
     } else {
       localStorage.clear();
     }
   });

   it('saveResumeData stores JSON and reference to last_session_id', () => {
     const config = { retries: 2 };
     const partialResults: TestResult[] = [];
     Helpers.saveResumeData(sessionId, 5, config, partialResults);

     expect(localStorage.getItem(`resume_${sessionId}`)).toBeTruthy();
     expect(localStorage.getItem('last_session_id')).toBe(sessionId);

     const parsed = JSON.parse(localStorage.getItem(`resume_${sessionId}`)!);
     expect(parsed.sessionId).toBe(sessionId);
     expect(parsed.lastCompletedIndex).toBe(5);
     expect(parsed.config).toEqual(config);
     expect(Array.isArray(parsed.partialResults)).toBe(true);
     expect(parsed.timestamp).toBeTruthy();
   });

   it('loadResumeData returns parsed object with Date timestamp when last_session_id is used', () => {
     // seed
     const timestamp = new Date('2025-01-02T03:04:05Z');
     localStorage.setItem('last_session_id', sessionId);
     localStorage.setItem(`resume_${sessionId}`, JSON.stringify({
       sessionId,
       lastCompletedIndex: 1,
       timestamp,
       config: { x: 1 },
       partialResults: []
     }));

     const loaded = Helpers.loadResumeData();
     expect(loaded).not.toBeNull();
     expect(loaded!.sessionId).toBe(sessionId);
     expect(loaded!.timestamp instanceof Date).toBe(true);
     expect(loaded!.timestamp.toISOString()).toBe(timestamp.toISOString());
   });

   it('loadResumeData returns null when data is missing or parse errors occur', () => {
     expect(Helpers.loadResumeData('missing')).toBeNull();
     localStorage.setItem('last_session_id', 'we-have-bad-json');
     localStorage.setItem('resume_we-have-bad-json', '{not-json');
     const spy = spyOn(console, 'error').mockImplementation(() => {});
     expect(Helpers.loadResumeData()).toBeNull();
     spy.mockRestore();
   });

   it('clearResumeData removes stored items and last_session_id if matching', () => {
     localStorage.setItem('last_session_id', sessionId);
     localStorage.setItem(`resume_${sessionId}`, '{"ok":true}');
     Helpers.clearResumeData(sessionId);
     expect(localStorage.getItem(`resume_${sessionId}`)).toBeNull();
     expect(localStorage.getItem('last_session_id')).toBeNull();
   });

   it('clearResumeData retains last_session_id if different session provided', () => {
     localStorage.setItem('last_session_id', 'other');
     localStorage.setItem('resume_other', '{"ok":true}');
     Helpers.clearResumeData('another');
     expect(localStorage.getItem('last_session_id')).toBe('other');
   });
 });

 describe('exportResults (JSON download)', () => {
   const makeSession = (): TestSession => ({
     id: 'session-1',
     startedAt: new Date('2025-08-23T00:00:00Z'),
     results: [
       {
         endpoint: { name: 'GetUsers', method: 'GET', path: '/users', category: 'Users' },
         status: 'success',
         requestTime: 10,
         responseTime: 20,
         totalTime: 30,
         timestamp: new Date('2025-08-23T00:00:01Z'),
       } as any
     ],
     config: { baseUrl: 'https://api.example.com' }
   });

   let createObjectURLSpy: any;
   let revokeObjectURLSpy: any;
   let createElementSpy: any;

   beforeEach(() => {
     // Mock URL methods
     createObjectURLSpy = spyOn(URL, 'createObjectURL').mockReturnValue('blob:url');
     revokeObjectURLSpy = spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

     // Spy on document.createElement to capture anchor and intercept click
     createElementSpy = spyOn(document, 'createElement').mockImplementation((tagName: any) => {
       const el = document.createElementNS('http://www.w3.org/1999/xhtml', tagName);
       if ((el as any).click) {
         (el as any).click = fn();
       } else {
         (el as any).click = fn();
       }
       return el as any;
     });
   });

   afterEach(() => {
     createObjectURLSpy.mockRestore();
     revokeObjectURLSpy.mockRestore();
     createElementSpy.mockRestore();
   });

   it('creates a JSON blob and triggers a download with expected filename', async () => {
     const sess = makeSession();
     Helpers.exportResults(sess);

     expect(createObjectURLSpy).toHaveBeenCalledTimes(1);

     // Check anchor creation and download attribute
     const anchorCalls = (createElementSpy as any).mock.calls.filter((args: any[]) => args[0] === 'a');
     expect(anchorCalls.length).toBeGreaterThan(0);

     // The most recent created anchor element
     const anchorEl = (createElementSpy as any).mock.results[anchorCalls.length - 1].value as HTMLAnchorElement;
     expect(anchorEl.download).toMatch(/^api_test_results_session-1_\d{4}-\d{2}-\d{2}\.json$/);
     expect(typeof anchorEl.click).toBe('function');

     // Validate blob content produced
     const blobArg = createObjectURLSpy.mock.calls[0][0] as Blob;
     expect(blobArg.type).toBe('application/json');

     // Read the blob text to assert structure
     const text = await (blobArg as any).text();
     const parsed = JSON.parse(text);
     expect(parsed.session.id).toBe('session-1');
     expect(parsed.session.results[0].timestamp).toBe('2025-08-23T00:00:01.000Z');
     expect(parsed.statistics.totalRequests).toBe(1);
     expect(parsed.exportedAt).toBeTruthy();
   });
 });

 describe('exportResultsCSV (CSV download)', () => {
   let createObjectURLSpy: any;
   let revokeObjectURLSpy: any;
   let createElementSpy: any;

   beforeEach(() => {
     createObjectURLSpy = spyOn(URL, 'createObjectURL').mockReturnValue('blob:url');
     revokeObjectURLSpy = spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
     createElementSpy = spyOn(document, 'createElement').mockImplementation((tagName: any) => {
       const el = document.createElementNS('http://www.w3.org/1999/xhtml', tagName);
       (el as any).click = fn();
       return el as any;
     });
   });

   afterEach(() => {
     createObjectURLSpy.mockRestore();
     revokeObjectURLSpy.mockRestore();
     createElementSpy.mockRestore();
   });

   it('creates a CSV blob with headers and one row, and triggers download', async () => {
     const results: TestResult[] = [
       {
         endpoint: { name: 'GetUsers', method: 'GET', path: '/users', category: 'Users' },
         status: 'success',
         requestTime: 10,
         responseTime: 20,
         totalTime: 30,
         timestamp: new Date('2025-08-23T00:00:01Z'),
         statusCode: 200,
         requestSize: 100,
         responseSize: 500,
         accuracyPercentage: 100
       } as any
     ];

     Helpers.exportResultsCSV(results);

     expect(createObjectURLSpy).toHaveBeenCalledTimes(1);
     const blobArg = createObjectURLSpy.mock.calls[0][0] as Blob;
     expect(blobArg.type).toBe('text/csv');

     const csv = await (blobArg as any).text();
     const lines = csv.trim().split('\n');
     expect(lines[0]).toContain('Timestamp,Endpoint Name,Method,Path,Category,Status');
     expect(lines[1]).toContain('"GetUsers"');
     expect(lines[1]).toContain('GET');
     expect(lines[1]).toContain('success');
     expect(lines[1]).toContain('/users');
   });
 });

 describe('deepClone', () => {
   it('clones primitives as-is', () => {
     expect(Helpers.deepClone(5)).toBe(5);
     expect(Helpers.deepClone('x')).toBe('x');
     expect(Helpers.deepClone(true)).toBe(true);
   });

   it('deeply clones nested objects and arrays without reference sharing', () => {
     const src = {
       a: 1,
       b: { c: [1, 2, { d: new Date('2020-01-01T00:00:00Z') }] },
       e: new Date('2025-08-23T00:00:00Z')
     };
     const cloned = Helpers.deepClone(src);
     expect(cloned).not.toBe(src);
     expect(cloned.b).not.toBe(src.b);
     expect(cloned.b.c).not.toBe(src.b.c);
     expect(cloned.b.c[2]).not.toBe(src.b.c[2]);
     expect((cloned.e as any).getTime()).toBe((src.e as any).getTime());

     // Mutate clone and ensure original unchanged
     (cloned as any).b.c[0] = 999;
     expect((src as any).b.c[0]).toBe(1);
   });
 });

 describe('debounce', () => {
   beforeEach(() => useFakeTimers());
   afterEach(() => runAllTimers());

   it('calls function only once after the wait time despite multiple rapid calls', () => {
     const cb = fn();
     const debounced = Helpers.debounce(cb as any, 200);

     debounced('a');
     debounced('b');
     debounced('c');

     // Not yet called
     expect(cb).not.toHaveBeenCalled();

     advanceTimersByTime(199);
     expect(cb).not.toHaveBeenCalled();

     advanceTimersByTime(1);
     expect(cb).toHaveBeenCalledTimes(1);

     // Verify last args are from the last call
     const lastCallArgs = (cb as any).mock.calls[(cb as any).mock.calls.length - 1];
     expect(lastCallArgs).toEqual(['c']);
   });
 });

 describe('throttle', () => {
   beforeEach(() => useFakeTimers());
   afterEach(() => runAllTimers());

   it('executes immediately and ignores subsequent calls within the limit', () => {
     const cb = fn();
     const throttled = Helpers.throttle(cb as any, 300);

     throttled('first');
     expect(cb).toHaveBeenCalledTimes(1);
     expect((cb as any).mock.calls[0]).toEqual(['first']);

     throttled('second');
     throttled('third');
     expect(cb).toHaveBeenCalledTimes(1);

     advanceTimersByTime(300);
     throttled('after');
     expect(cb).toHaveBeenCalledTimes(2);
     expect((cb as any).mock.calls[1]).toEqual(['after']);
   });
 });

 describe('getStatusColor', () => {
   it('returns color codes for known statuses and default for unknown', () => {
     expect(Helpers.getStatusColor('success')).toBe('#10b981');
     expect(Helpers.getStatusColor('error')).toBe('#ef4444');
     expect(Helpers.getStatusColor('timeout')).toBe('#f59e0b');
     expect(Helpers.getStatusColor('pending')).toBe('#6b7280');
     expect(Helpers.getStatusColor('unknown')).toBe('#6b7280');
   });
 });

 describe('getAccuracyColor', () => {
   it('maps accuracy thresholds to colors', () => {
     expect(Helpers.getAccuracyColor(95)).toBe('#10b981'); // >= 90
     expect(Helpers.getAccuracyColor(70)).toBe('#f59e0b'); // >= 70
     expect(Helpers.getAccuracyColor(50)).toBe('#f97316'); // >= 50
     expect(Helpers.getAccuracyColor(49)).toBe('#ef4444'); // < 50
   });
 });

 describe('isValidUrl', () => {
   it('validates proper URLs', () => {
     expect(Helpers.isValidUrl('https://example.com')).toBe(true);
     expect(Helpers.isValidUrl('http://localhost:3000/path?x=1#hash')).toBe(true);
   });

   it('rejects invalid URLs', () => {
     expect(Helpers.isValidUrl('not a url')).toBe(false);
     expect(Helpers.isValidUrl('ht!tp://bad')).toBe(false);
   });
 });

 describe('generateTestPayload', () => {
   const origNow = Date.now;
   beforeAll(() => {
     // Freeze time for deterministic string payloads
     setSystemTime(new Date('2025-08-23T00:00:00Z'));
   });
   afterAll(() => {
     if (_isVitest) vi.useRealTimers();
     if (_isJest) jest.useRealTimers();
     // @ts-ignore
     Date.now = origNow;
   });

   it('returns undefined when endpoint has no payload definition', () => {
     expect(Helpers.generateTestPayload({})).toBeUndefined();
   });

   it('generates fields by type, including Blob for "file"', () => {
     const payload = Helpers.generateTestPayload({
       payload: {
         s: 'string',
         n: 'number',
         b: 'boolean',
         arr: 'array',
         obj: 'object',
         f: 'file',
         unknown: 'customType'
       }
     });

     expect(typeof payload.s).toBe('string');
     expect(Number.isFinite(payload.n)).toBe(true);
     expect(typeof payload.b).toBe('boolean');
     expect(Array.isArray(payload.arr)).toBe(true);
     expect(typeof payload.obj).toBe('object');
     expect(payload.f).toBeInstanceOf(Blob);
     expect(typeof payload.unknown).toBe('string');

     // Check string prefixes roughly
     expect(payload.s).toContain('test_s_');
     expect(payload.unknown).toContain('test_customType_');
   });
 });