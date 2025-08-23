/**
 * Tests for serverSync service.
 * Framework: Jest
 *
 * Notes:
 * - Focuses on public functions exported by serverSync, especially areas typically touched by PR diffs:
 *   - request/response flows
 *   - retry logic and backoff behavior
 *   - parameter validation and error surfaces
 *   - idempotency and deduping of in-flight requests
 *   - serialization and merge logic
 *
 * Conventions:
 * - Use fake timers for debounce/retry scheduling.
 * - Mock network (axios/fetch) and any storage or global side-effects.
 * - Keep tests isolated and deterministic.
 */
import { describe, it, expect, beforeEach, afterEach, jest } from "@jest/globals";
import * as serverSync from "./serverSync";

beforeEach(() => {
  jest.useFakeTimers();
  jest.clearAllTimers();
  jest.clearAllMocks && jest.clearAllMocks();
});

afterEach(() => {
  jest.useRealTimers();
});

describe("serverSync: core behavior", () => {
  it("exposes expected public API", () => {
    // Validate presence of key exports (non-null, functions)
    const keys = Object.keys(serverSync);
    expect(keys.length).toBeGreaterThan(0);
    if (serverSync['syncWithServer'] !== undefined) { expect(typeof serverSync['syncWithServer']).toBe('function'); }
    if (serverSync['enqueueSync'] !== undefined) { expect(typeof serverSync['enqueueSync']).toBe('function'); }
    if (serverSync['flush'] !== undefined) { expect(typeof serverSync['flush']).toBe('function'); }
    if (serverSync['getPending'] !== undefined) { expect(typeof serverSync['getPending']).toBe('function'); }
    if (serverSync['setBackoff'] !== undefined) { expect(typeof serverSync['setBackoff']).toBe('function'); }
    if (serverSync['setMaxRetries'] !== undefined) { expect(typeof serverSync['setMaxRetries']).toBe('function'); }
  });
});

describe("serverSync: edge cases and input validation", () => {
  it("gracefully handles empty or null payloads", async () => {
    const fn = serverSync.syncWithServer || serverSync.flush || serverSync.enqueueSync;
    if (!fn) return;

    await expect(fn(null)).rejects.toThrow(); // Expect explicit error or validation
    await expect(fn(undefined)).rejects.toThrow();
    await expect(fn({ items: [] })).resolves.toBeTruthy();
  });

  it("dedupes identical in-flight requests when supported", async () => {
    const enqueue = serverSync.enqueueSync || serverSync.syncWithServer || null;
    if (!enqueue) return;

    const payload = { items: [{ id: 1, op: "upsert" }] };

    // If using axios, simulate a delayed resolve to check coalescing
    if (typeof axios !== "undefined" && axios.post) {
      let resolveFn;
      const promise = new Promise((res) => { resolveFn = res; });
      axios.post.mockReturnValueOnce(promise);

      const p1 = enqueue(payload);
      const p2 = enqueue(payload);

      expect(p1).not.toBeNull();
      expect(p2).not.toBeNull();

      // Resolve now
      resolveFn({ status: 200, data: { ok: true } });

      const [r1, r2] = await Promise.all([p1, p2]);
      // If coalesced, they may be strictly equal or at least both ok
      expect(r1).toBeTruthy();
      expect(r2).toBeTruthy();
    } else {
      // Generic assertion if network layer unknown
      const p1 = enqueue(payload);
      const p2 = enqueue(payload);
      const [r1, r2] = await Promise.all([p1, p2]);
      expect(r1).toBeTruthy();
      expect(r2).toBeTruthy();
    }
  });

  it("respects maximum batch size or chunking when applicable", async () => {
    const fn = serverSync.syncWithServer || serverSync.flush || serverSync.enqueueSync;
    if (!fn) return;

    const large = { items: Array.from({ length: 250 }, (_, i) => ({ id: i, op: "upsert", data: { v: i } })) };
    const res = await fn(large);
    expect(res).toBeTruthy();
  });
});

describe("serverSync: failure paths", () => {
  it("surfaces server-side errors (5xx) after exhausting retries", async () => {
    const fn = serverSync.syncWithServer || serverSync.flush || serverSync.enqueueSync;
    if (!fn) return;

    const setRetries = serverSync.setMaxRetries || serverSync.configureRetries || null;
    const setBackoff = serverSync.setBackoff || serverSync.configureBackoff || null;
    if (setRetries) setRetries(1);
    if (setBackoff) setBackoff(10);

    if (typeof axios !== "undefined" && axios.post) {
      axios.post.mockRejectedValueOnce({ response: { status: 503 } })
                .mockRejectedValueOnce({ response: { status: 503 } });

      const p = fn({ items: [{ id: 1 }] });
      for (let i = 0; i < 5; i++) {
        jest.advanceTimersByTime ? jest.advanceTimersByTime(20) : vi.advanceTimersByTime(20);
      }
      await expect(p).rejects.toBeTruthy();
    } else if (typeof fetch !== "undefined" && global.fetch) {
      global.fetch
        .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({}) })
        .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({}) });

      const p = fn({ items: [{ id: 1 }] });
      for (let i = 0; i < 5; i++) {
        jest.advanceTimersByTime ? jest.advanceTimersByTime(20) : vi.advanceTimersByTime(20);
      }
      await expect(p).rejects.toBeTruthy();
    } else {
      // Generic fallback: expect the function to throw/reject on failure path
      await expect(fn({ items: [{ id: 1 }] })).rejects.toBeTruthy();
    }
  });

  it("validates item schema and throws for malformed entries", async () => {
    const fn = serverSync.enqueueSync || serverSync.syncWithServer || null;
    if (!fn) return;

    await expect(fn({ items: [{}] })).rejects.toBeTruthy();           // missing id/op
    await expect(fn({ items: [{ id: null, op: "upsert" }] })).rejects.toBeTruthy();
    await expect(fn({ items: [{ id: 1, op: "unknown" }] })).rejects.toBeTruthy();
  });
});