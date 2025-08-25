These tests target AudioService and run under Jest via react-scripts (jsdom).

The mocks include:
- `navigator.mediaDevices.getUserMedia()`
- `MediaRecorder` (with simple `dataavailable`/`stop` event simulation)
- `URL.createObjectURL()` / `URL.revokeObjectURL()`
- `document.createElement('a').click()` for download behavior

Reusable mocks live in `src/test-utils/mediaMocks.ts`.