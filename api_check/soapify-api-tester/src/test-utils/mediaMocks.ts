/* Test utilities: Browser media API mocks for Jest (jsdom) */
export class MockMediaRecorder {
  public static isTypeSupported = (_type: string) => true;

  private listeners: Record<string, Function[]> = {};
  public state: 'inactive' | 'recording' | 'paused' = 'inactive';
  public stream: MediaStream;
  private intervalId: any;

  constructor(stream: MediaStream, _options?: MediaRecorderOptions) {
    this.stream = stream;
  }

  start(timeslice?: number) {
    this.state = 'recording';
    const emit = () => {
      const chunk = new Blob([new Uint8Array([1,2,3])], { type: 'audio/wav' });
      this.dispatchEvent('dataavailable', { data: chunk });
    };
    if (timeslice) {
      this.intervalId = setInterval(emit, timeslice);
    } else {
      setTimeout(emit, 10);
    }
  }

  stop() {
    if (this.intervalId) clearInterval(this.intervalId);
    this.state = 'inactive';
    this.dispatchEvent('stop', {});
  }

  pause() {
    if (this.state !== 'recording') throw new Error('Invalid state');
    this.state = 'paused';
  }

  resume() {
    if (this.state !== 'paused') throw new Error('Invalid state');
    this.state = 'recording';
  }

  addEventListener(type: string, cb: any, _opts?: any) {
    if (!this.listeners[type]) this.listeners[type] = [];
    this.listeners[type].push(cb);
  }
  removeEventListener(type: string, cb: any) {
    this.listeners[type] = (this.listeners[type] || []).filter(fn => fn !== cb);
  }
  dispatchEvent(type: string, event: any) {
    (this.listeners[type] || []).forEach(fn => fn(event));
  }
}

export function installMediaAPIMocks() {
  // Fake stream with stoppable track
  const fakeStream: MediaStream = {
    getAudioTracks: () => [] as any,
    getVideoTracks: () => [] as any,
    getTracks: () => [{ stop: () => {} } as any],
    addTrack: () => {},
    removeTrack: () => {},
    onaddtrack: null as any,
    onremovetrack: null as any,
    active: true,
    id: 'mock-stream'
  } as any;

  Object.defineProperty(global, 'navigator', {
    value: {
      mediaDevices: {
        getUserMedia: jest.fn().mockResolvedValue(fakeStream)
      }
    },
    writable: true
  });

  // MediaRecorder
  (global as any).MediaRecorder = MockMediaRecorder as any;

  // URL.createObjectURL / revokeObjectURL
  const createdUrls: string[] = [];
  (global as any).URL = {
    createObjectURL: jest.fn().mockImplementation((_blob: Blob) => {
      const u = `blob:mock://${Math.random().toString(36).slice(2)}`;
      createdUrls.push(u);
      return u;
    }),
    revokeObjectURL: jest.fn().mockImplementation((u: string) => {
      const idx = createdUrls.indexOf(u);
      if (idx >= 0) createdUrls.splice(idx, 1);
    })
  } as any;

  // Ensure clean storage
  localStorage.clear();
}

export function installDomDownloadMocks() {
  // Safely clear document body by removing all child nodes
  while (document.body.firstChild) {
    document.body.removeChild(document.body.firstChild);
  }
  const clicks: string[] = [];
  const createElement = document.createElement.bind(document);
  jest.spyOn(document, 'createElement').mockImplementation((tag: any) => {
    if (tag !== 'a') return createElement(tag);
    const a = createElement('a') as HTMLAnchorElement;
    const origClick = a.click.bind(a);
    a.click = () => {
      clicks.push(a.href);
      origClick();
    };
    return a;
  });
  return { clicks };
}