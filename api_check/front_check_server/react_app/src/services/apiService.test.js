/* eslint-disable @typescript-eslint/no-var-requires */
/**
 * Tests for apiService
 * Framework: Jest (React app default). This suite covers:
 * - GET/POST/PUT/DELETE happy paths
 * - Query and path parameter handling
 * - Error normalization for non-2xx
 * - Network failures and timeouts
 * - Environment-driven base URL
 * - Input validation and unexpected inputs
 *
 * We mock the underlying API client used by apiService via jest.doMock.
 */

describe("apiService", () => {
  let originalEnv;

  beforeAll(() => {
    originalEnv = { ...process.env };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
  });

  test("get: returns parsed JSON on 200 OK", async () => {
    jest.doMock("./apiClient", () => ({
      get: jest.fn().mockResolvedValue({ status: 200, data: { ok: true } }),
      post: jest.fn(),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.get("/status")).resolves.toEqual({ ok: true });
  });

  test("get: appends and encodes query params", async () => {
    const getSpy = jest.fn().mockResolvedValue({ status: 200, data: {} });
    jest.doMock("./apiClient", () => ({
      get: getSpy,
      post: jest.fn(),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await apiService.get("/search", { q: "hello world", filter: "a&b" });

    const urlArg = getSpy.mock.calls[0][0];
    if (typeof urlArg === "string") {
      expect(urlArg).toMatch(/q=hello%20world/);
      expect(urlArg).toMatch(/filter=a%26b/);
    } else {
      const params = getSpy.mock.calls[0][1]?.params;
      expect(params).toMatchObject({ q: "hello world", filter: "a&b" });
    }
  });

  test("post: sends JSON body, returns created entity", async () => {
    const payload = { title: "New" };
    jest.doMock("./apiClient", () => ({
      get: jest.fn(),
      post: jest.fn().mockResolvedValue({ status: 201, data: { id: "1", ...payload } }),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.post("/items", payload)).resolves.toEqual(expect.objectContaining({ id: "1" }));
  });

  test("put: sends JSON body, returns updated", async () => {
    jest.doMock("./apiClient", () => ({
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn().mockResolvedValue({ status: 200, data: { updated: true } }),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.put("/items/1", { title: "Edit" })).resolves.toEqual({ updated: true });
  });

  test("delete: resolves truthy for 204 and 200", async () => {
    const delSpy = jest.fn()
      .mockResolvedValueOnce({ status: 204, data: null })
      .mockResolvedValueOnce({ status: 200, data: { ok: true } });
    jest.doMock("./apiClient", () => ({
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      del: delSpy,
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.delete("/items/1")).resolves.toBeTruthy();
    await expect(apiService.delete("/items/2")).resolves.toBeTruthy();
  });

  test("throws normalized error on non-2xx", async () => {
    jest.doMock("./apiClient", () => ({
      get: jest.fn().mockResolvedValue({ status: 400, data: { error: "Bad input" } }),
      post: jest.fn(),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.get("/bad")).rejects.toMatchObject({ status: 400 });
  });

  test("bubbles up network rejection with code/message", async () => {
    const err = Object.assign(new Error("timeout"), { code: "ETIMEDOUT" });
    jest.doMock("./apiClient", () => ({
      get: jest.fn().mockRejectedValue(err),
      post: jest.fn(),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.get("/slow")).rejects.toHaveProperty("code", "ETIMEDOUT");
  });

  test("uses REACT_APP_API_BASE_URL when present", async () => {
    process.env.REACT_APP_API_BASE_URL = "https://example.test/api";
    const getSpy = jest.fn().mockResolvedValue({ status: 200, data: {} });

    jest.doMock("./apiClient", () => ({
      get: getSpy,
      post: jest.fn(),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await apiService.get("/ping");
    const urlArg = getSpy.mock.calls[0][0];
    if (typeof urlArg === "string") {
      expect(urlArg.startsWith("https://example.test/api/")).toBe(true);
    }
  });

  test("rejects on unexpected inputs", async () => {
    jest.doMock("./apiClient", () => ({
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      del: jest.fn(),
    }), { virtual: true });

    const { default: apiService } = await import("./apiService");
    await expect(apiService.get(undefined)).rejects.toBeTruthy();
    await expect(apiService.post("/x", undefined)).rejects.toBeTruthy();
  });
});