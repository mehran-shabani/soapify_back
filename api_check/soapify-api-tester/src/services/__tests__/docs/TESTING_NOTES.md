Testing Notes
- Framework detected: Jest via create-react-app (react-scripts test).
- New tests live at src/services/__tests__/apiService.spec.ts and cover:
  - testEndpoint (success, GET omission, Axios errors, timeouts, non-Axios errors)
  - testMultipleEndpoints (sequential vs. concurrent with progress)
  - testWithRetries (success after retries, all-fail path with last error)
  - updateConfig and cancelCurrentRequests behaviors
  - request/response size calculations (indirect verification)
- External dependencies axios and utils/helpers are mocked with jest.mock.
- Target under test: src/services/apiService.ts (exports ApiService as default and named).