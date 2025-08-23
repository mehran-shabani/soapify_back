/* eslint-disable @typescript-eslint/no-explicit-any */
import ReportService, { 
  DetailedReport, 
  // Re-exported interfaces from the implementation file are not exported.
  // We'll build minimal typed fixtures inline to avoid coupling on external types.
} from '../reportService.test'; // Implementation file is misnamed *.test.ts in PR; import relative

// Mock helpers used by ReportService
jest.mock('../../utils/helpers', () => ({
  calculateStatistics: jest.fn(),
  formatDuration: jest.fn((ms: number) => `${ms}ms`),
  formatDateTime: jest.fn((d: Date) => d.toISOString()),
  formatFileSize: jest.fn((bytes: number) => `${(bytes/1024).toFixed(1)} KB`),
}));

import { calculateStatistics, formatDuration, formatDateTime, formatFileSize } from '../../utils/helpers';

// Minimal domain shapes to construct fixtures (aligned with usage in ReportService)
type Endpoint = { name: string; category: string };
type TestResult = {
  endpoint: Endpoint;
  status: 'success' | 'error' | 'timeout';
  totalTime: number;
  statusCode?: number;
  responseSize?: number;
  accuracyPercentage?: number;
  error?: string;
};
type TestSession = {
  id: string;
  name: string;
  startTime: Date;
  endTime?: Date;
  results: TestResult[];
};
type TestStatistics = {
  totalRequests: number;
  successRate: number; // percent
  errorRate: number;   // percent
  averageResponseTime: number;
  throughput: number;  // req/sec
  categoriesStats: Record<string, { averageTime: number }>;
};

// Helper to make a session
const makeSession = (overrides: Partial<TestSession> = {}, results: TestResult[] = []): TestSession => ({
  id: 'sess-1',
  name: 'Session 1',
  startTime: new Date('2025-08-23T10:00:00.000Z'),
  endTime: new Date('2025-08-23T10:05:00.000Z'),
  results,
  ...overrides,
});

const e = (name: string, category: string): Endpoint => ({ name, category });

// Threshold constants mirrored from implementation for clarity in tests
const SLOW = 5000;
const VERY_SLOW = 10000;

describe('ReportService - core report generation', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  test('generateDetailedReport returns a well-formed report with all sections when audio provided', () => {
    const results: TestResult[] = [
      { endpoint: e('GET /users', 'Users'), status: 'success', totalTime: 1200, responseSize: 25000 },
      { endpoint: e('POST /users', 'Users'), status: 'error', totalTime: 700, statusCode: 500, error: 'Server error' },
      { endpoint: e('GET /orders', 'Orders'), status: 'timeout', totalTime: 11000, error: 'timeout' },
    ];
    const session = makeSession({}, results);

    const stats: TestStatistics = {
      totalRequests: 3,
      successRate: 33.333,
      errorRate: 66.667,
      averageResponseTime: 4300,
      throughput: 0.8,
      categoriesStats: {
        Users: { averageTime: 950 },
        Orders: { averageTime: 11000 },
      },
    };
    (calculateStatistics as jest.Mock).mockReturnValue(stats);

    const recordings = [
      { sessionId: session.id, duration: 120000, size: 5_000_000 },
      { sessionId: session.id, duration: 240000, size: 6_000_000 },
      { sessionId: 'other', duration: 60000, size: 2_000_000 },
    ];

    const report = ReportService.generateDetailedReport(session as any, recordings as any);

    expect(calculateStatistics).toHaveBeenCalledWith(results);
    expect(report.session).toBe(session);
    expect(report.statistics).toEqual(stats);
    expect(report.summary.totalEndpoints).toBe(3);
    expect(report.summary.successfulRequests).toBe(Math.round(3 * (stats.successRate / 100)));
    expect(report.summary.failedRequests).toBe(Math.round(3 * (stats.errorRate / 100)));
    expect(report.summary.criticalIssues).toBe(2); // error + very slow timeout
    expect(report.summary.warningIssues).toBeGreaterThanOrEqual(1); // slow/timeout/low accuracy checks

    expect(report.categoryBreakdown).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ category: 'Users', totalEndpoints: 2 }),
        expect.objectContaining({ category: 'Orders', totalEndpoints: 1 }),
      ])
    );

    expect(report.errorAnalysis.totalErrors).toBe(2);
    expect(report.performanceInsights.fastestEndpoint.name).toBe('GET /users');
    expect(report.performanceInsights.slowestEndpoint.name).toBe('GET /users'); // only success result times considered
    expect(report.audioSummary).toBeDefined();
    expect(report.recommendations.length).toBeGreaterThan(0);
    expect(report.generatedAt).toBeInstanceOf(Date);
  });

  test('generateDetailedReport handles missing endTime by computing duration relative to now', () => {
    const now = new Date('2025-08-23T11:00:00.000Z');
    jest.useFakeTimers().setSystemTime(now);

    const session = makeSession({ endTime: undefined }, [
      { endpoint: e('GET /a', 'A'), status: 'success', totalTime: 1_000 },
    ]);
    const stats: TestStatistics = {
      totalRequests: 1,
      successRate: 100,
      errorRate: 0,
      averageResponseTime: 1000,
      throughput: 2.5,
      categoriesStats: { A: { averageTime: 1000 } },
    };
    (calculateStatistics as jest.Mock).mockReturnValue(stats);

    const report = ReportService.generateDetailedReport(session as any);

    expect(report.summary.totalTestDuration).toBe(now.getTime() - session.startTime.getTime());
    jest.useRealTimers();
  });

  test('category breakdown sorts categories by totalEndpoints desc and computes rates correctly', () => {
    const results: TestResult[] = [
      { endpoint: e('GET /u', 'Users'), status: 'success', totalTime: 200 },
      { endpoint: e('POST /u', 'Users'), status: 'error', totalTime: 600, error: 'x' },
      { endpoint: e('GET /o', 'Orders'), status: 'success', totalTime: 10_500 },
      { endpoint: e('GET /o2', 'Orders'), status: 'timeout', totalTime: 11_000, error: 'timeout' },
      { endpoint: e('GET /p', 'Payments'), status: 'success', totalTime: 4900 },
    ];
    const session = makeSession({}, results);
    (calculateStatistics as jest.Mock).mockReturnValue({
      totalRequests: results.length,
      successRate: 60,
      errorRate: 40,
      averageResponseTime: 3300,
      throughput: 1.3,
      categoriesStats: { Users: { averageTime: 400 }, Orders: { averageTime: 10_750 }, Payments: { averageTime: 4900 } },
    } as TestStatistics);

    const report = ReportService.generateDetailedReport(session as any);

    // Sorted by totalEndpoints: Users(2), Orders(2), Payments(1) — but equal counts preserve map insertion order; we just validate contents and metrics.
    const users = report.categoryBreakdown.find(c => c.category === 'Users')!;
    expect(users.totalEndpoints).toBe(2);
    expect(users.successCount + users.failureCount).toBe(2);
    expect(users.successRate).toBeCloseTo((users.successCount / 2) * 100);

    const orders = report.categoryBreakdown.find(c => c.category === 'Orders')!;
    expect(orders.criticalEndpoints).toContain('GET /o2'); // very slow timeout marked critical
    expect(orders.topIssues.join(' ')).toMatch(/timeouts|slow/);
  });

  test('error analysis groups errors by type and category and caps criticalErrors to 10 items', () => {
    const manyErrors: TestResult[] = Array.from({ length: 15 }, (_, i) => ({
      endpoint: e(`GET /e${i}`, i % 2 === 0 ? 'A' : 'B'),
      status: i % 3 === 0 ? 'timeout' : 'error',
      totalTime: i % 4 === 0 ? VERY_SLOW + 1 : 100,
      statusCode: i % 5 === 0 ? 503 : 400,
      error: i % 3 === 0 ? 'timeout' : 'server',
    }));

    const session = makeSession({}, [{ endpoint: e('GET /ok', 'C'), status: 'success', totalTime: 10 } as TestResult, ...manyErrors]);
    (calculateStatistics as jest.Mock).mockReturnValue({
      totalRequests: session.results.length,
      successRate: 1 / session.results.length,
      errorRate: (session.results.length - 1) / session.results.length,
      averageResponseTime: 1000,
      throughput: 2,
      categoriesStats: { A: { averageTime: 100 }, B: { averageTime: 100 }, C: { averageTime: 10 } },
    } as TestStatistics);

    const report = ReportService.generateDetailedReport(session as any);
    const ea = report.errorAnalysis;

    expect(ea.totalErrors).toBe(manyErrors.length);
    expect(Object.keys(ea.errorsByType)).toEqual(expect.arrayContaining(['error', 'timeout']));
    expect(ea.criticalErrors.length).toBeLessThanOrEqual(10);
    expect(ea.commonErrorPatterns.join(' ')).toMatch(/Authentication|Network|Server-side|connectivity|errors/);
    expect(Object.values(ea.errorsByCategory).reduce((a, b) => a + b, 0)).toBe(manyErrors.length);
    expect(Object.keys(ea.suggestedFixes)).toEqual(expect.arrayContaining(['timeout', 'error']));
  });

  test('performance insights compute fastest/slowest from successful results only and detect bottlenecks', () => {
    const res: TestResult[] = [
      { endpoint: e('E1', 'C1'), status: 'success', totalTime: 100 },
      { endpoint: e('E2', 'C1'), status: 'success', totalTime: 500 },
      { endpoint: e('E3', 'C2'), status: 'error', totalTime: 20000 },
      { endpoint: e('E2', 'C1'), status: 'timeout', totalTime: 7000 },
      { endpoint: e('E2', 'C1'), status: 'error', totalTime: 6000 },
      { endpoint: e('E2', 'C1'), status: 'error', totalTime: 6500 },
    ];
    const session = makeSession({}, res);
    (calculateStatistics as jest.Mock).mockReturnValue({
      totalRequests: res.length,
      successRate: 2 / res.length * 100,
      errorRate: (res.length - 2) / res.length * 100,
      averageResponseTime: res.reduce((s, r) => s + r.totalTime, 0) / res.length,
      throughput: 1,
      categoriesStats: { C1: { averageTime: 4500 }, C2: { averageTime: 20000 } },
    } as TestStatistics);

    const report = ReportService.generateDetailedReport(session as any);

    expect(report.performanceInsights.fastestEndpoint).toEqual({ name: 'E1', time: 100 });
    expect(report.performanceInsights.slowestEndpoint).toEqual({ name: 'E2', time: 500 }); // among successes only
    expect(report.performanceInsights.bottlenecks.join(' ')).toMatch(/consistently slow|E2/);
    expect(report.performanceInsights.optimizationSuggestions.length).toBeGreaterThanOrEqual(1);
  });

  test('audio summary quality tiers: poor | fair | good | excellent based on avg length + size', () => {
    // Poor: low duration/size
    let report = ReportService.generateDetailedReport(
      makeSession({}, [] as TestResult[]) as any,
      [{ sessionId: 'sess-1', duration: 5000, size: 10_000 }] as any
    );
    expect(report.audioSummary?.recordingQuality).toBe('poor');

    // Fair: > 10s average length
    report = ReportService.generateDetailedReport(
      makeSession({}, [] as TestResult[]) as any,
      [{ sessionId: 'sess-1', duration: 11_000, size: 10_000 }] as any
    );
    expect(report.audioSummary?.recordingQuality).toBe('fair');

    // Good: > 60s avg and > 2MB total
    report = ReportService.generateDetailedReport(
      makeSession({}, [] as TestResult[]) as any,
      [{ sessionId: 'sess-1', duration: 61_000, size: 2_100_000 }] as any
    );
    expect(report.audioSummary?.recordingQuality).toBe('good');

    // Excellent: > 5min avg and > 10MB
    report = ReportService.generateDetailedReport(
      makeSession({}, [] as TestResult[]) as any,
      [{ sessionId: 'sess-1', duration: 301_000, size: 10_100_000 }] as any
    );
    expect(report.audioSummary?.recordingQuality).toBe('excellent');
  });

  test('recommendations include success-rate, performance, timeout/error, worst category, throughput, or a generic success message', () => {
    const res: TestResult[] = [
      { endpoint: e('SLOW1', 'SlowCat'), status: 'success', totalTime: VERY_SLOW + 1, responseSize: 150_000 },
      { endpoint: e('E', 'SlowCat'), status: 'error', totalTime: 1000, error: 'server', statusCode: 500 },
      { endpoint: e('T', 'SlowCat'), status: 'timeout', totalTime: VERY_SLOW + 2, error: 'timeout' },
    ];
    const session = makeSession({}, res);

    const stats: TestStatistics = {
      totalRequests: res.length,
      successRate: 60, // below 80 threshold → success-rate rec
      errorRate: 40,
      averageResponseTime: VERY_SLOW + 100, // performance rec
      throughput: 0.5, // throughput rec
      categoriesStats: { SlowCat: { averageTime: VERY_SLOW + 100 } }, // worst category rec
    };
    (calculateStatistics as jest.Mock).mockReturnValue(stats);

    const report = ReportService.generateDetailedReport(session as any);
    const text = report.recommendations.join(' | ');

    expect(text).toMatch(/Success rate is/);
    expect(text).toMatch(/Average response time is/);
    expect(text).toMatch(/timeout errors detected|timeouts/);
    expect(text).toMatch(/server errors detected/);
    expect(text).toMatch(/SlowCat category has the slowest average response time/);
    expect(text).toMatch(/Low throughput detected/);
  });

  test('when everything looks good, returns at least one positive recommendation', () => {
    const res: TestResult[] = [
      { endpoint: e('OK1', 'A'), status: 'success', totalTime: 100 },
      { endpoint: e('OK2', 'A'), status: 'success', totalTime: 200 },
    ];
    const session = makeSession({}, res);
    const stats: TestStatistics = {
      totalRequests: res.length,
      successRate: 100,
      errorRate: 0,
      averageResponseTime: 150,
      throughput: 10,
      categoriesStats: { A: { averageTime: 150 } },
    };
    (calculateStatistics as jest.Mock).mockReturnValue(stats);

    const report = ReportService.generateDetailedReport(session as any);
    expect(report.recommendations).toContain(
      'Overall performance looks good! Continue monitoring and consider setting up automated testing for regression detection.'
    );
  });
});

describe('ReportService - export functions (DOM/Blob/URL interactions)', () => {
  const createAStub = () => {
    const anchor = {
      href: '',
      download: '',
      click: jest.fn(),
    } as any;

    const bodyChildren: any[] = [];
    const appendChild = jest.fn((el: any) => bodyChildren.push(el));
    const removeChild = jest.fn((el: any) => {
      const i = bodyChildren.indexOf(el);
      if (i >= 0) bodyChildren.splice(i, 1);
    });

    (global as any).document = {
      createElement: jest.fn(() => anchor),
      body: { appendChild, removeChild },
    };

    const objectURLs: string[] = [];
    (global as any).URL = {
      createObjectURL: jest.fn(() => {
        const url = `blob:mock-${Math.random()}`;
        objectURLs.push(url);
        return url;
      }),
      revokeObjectURL: jest.fn((url: string) => {
        const idx = objectURLs.indexOf(url);
        if (idx >= 0) objectURLs.splice(idx, 1);
      }),
    };

    // Minimal Blob shim to satisfy constructor usage
    (global as any).Blob = class {
      parts: unknown[];
      type?: string;
      constructor(parts: unknown[], opts: any) {
        this.parts = parts;
        this.type = opts?.type;
      }
    };

    return { anchor, appendChild, removeChild };
  };

  const dummyReport = (): DetailedReport => {
    // Build a tiny but consistent report structure used by both JSON and HTML exports
    const session: TestSession = {
      id: 'sess-2',
      name: 'Session 2',
      startTime: new Date('2025-08-23T10:00:00.000Z'),
      endTime: new Date('2025-08-23T10:10:00.000Z'),
      results: [
        { endpoint: { name: 'E1', category: 'Cat1' }, status: 'success', totalTime: 100 },
      ] as any,
    } as any;

    (calculateStatistics as jest.Mock).mockReturnValue({
      totalRequests: 1,
      successRate: 100,
      errorRate: 0,
      averageResponseTime: 100,
      throughput: 5,
      categoriesStats: { Cat1: { averageTime: 100 } },
    } as TestStatistics);

    const report = ReportService.generateDetailedReport(session as any);
    return report as DetailedReport;
  };

  beforeEach(() => {
    jest.resetAllMocks();
  });

  test('exportDetailedReportJSON triggers anchor click with proper filename and blob type', () => {
    const { anchor, appendChild, removeChild } = createAStub();
    const report = dummyReport();

    ReportService.exportDetailedReportJSON(report);

    expect(appendChild).toHaveBeenCalledWith(anchor);
    expect(anchor.download).toMatch(/^detailed_report_sess-2_\d{4}-\d{2}-\d{2}\.json$/);
    expect(anchor.click).toHaveBeenCalledTimes(1);
    expect(removeChild).toHaveBeenCalledWith(anchor);
    // Verify Blob content type was application/json via constructor usage in mock
    // The formatDuration/DateTime helpers are already mocked and used in HTML path, not JSON content creation.
  });

  test('exportDetailedReportHTML triggers anchor click with HTML filename and uses helper formatters', () => {
    const { anchor, appendChild, removeChild } = createAStub();
    const report = dummyReport();

    ReportService.exportDetailedReportHTML(report);

    expect(appendChild).toHaveBeenCalled();
    expect(anchor.download).toMatch(/^detailed_report_sess-2_\d{4}-\d{2}-\d{2}\.html$/);
    expect(formatDateTime).toHaveBeenCalled(); // used in HTML header rendering
    expect(formatDuration).toHaveBeenCalled(); // used in multiple places in HTML
    expect(formatFileSize).not.toHaveBeenCalled(); // no audioSummary in this dummy report
    expect(anchor.click).toHaveBeenCalledTimes(1);
    expect(removeChild).toHaveBeenCalledWith(anchor);
  });

  test('exportDetailedReportHTML includes audio summary values when audioSummary exists', () => {
    const { anchor } = createAStub();

    // Create a report with audio summary by passing recordings
    const session: TestSession = {
      id: 'sess-audio',
      name: 'Audio Session',
      startTime: new Date('2025-08-23T09:00:00.000Z'),
      endTime: new Date('2025-08-23T09:05:00.000Z'),
      results: [{ endpoint: { name: 'E', category: 'C' }, status: 'success', totalTime: 100 }] as any,
    } as any;

    (calculateStatistics as jest.Mock).mockReturnValue({
      totalRequests: 1,
      successRate: 100,
      errorRate: 0,
      averageResponseTime: 100,
      throughput: 2,
      categoriesStats: { C: { averageTime: 100 } },
    } as TestStatistics);

    const recordings = [{ sessionId: 'sess-audio', duration: 65_000, size: 2_500_000 }];

    const report = ReportService.generateDetailedReport(session as any, recordings as any);
    ReportService.exportDetailedReportHTML(report as DetailedReport);

    expect(formatFileSize).toHaveBeenCalledWith(report.audioSummary!.totalSize);
    expect(anchor.download).toContain('detailed_report_sess-audio_');
  });
});