/**
 * AudioService unit tests.
 * Test framework: Jest via react-scripts (jsdom).
 * We mock MediaRecorder, navigator.mediaDevices.getUserMedia, URL, document anchor, and localStorage.
 */
import AudioService from '../audioService';
import type { AudioRecording } from '../../types';
import { installMediaAPIMocks, installDomDownloadMocks, MockMediaRecorder } from '../../test-utils/mediaMocks';

describe('AudioService', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.restoreAllMocks();
    installMediaAPIMocks();
  });

  test('startRecording initializes, tracks status, persists stub recording, and fires onRecordingStart', async () => {
    const svc = new AudioService();
    const onStart = jest.fn();
    svc.setCallbacks({ onRecordingStart: onStart });

    const rec = await svc.startRecording('sess-1', 'wav');

    expect(rec.sessionId).toBe('sess-1');
    expect(rec.format).toBe('wav');
    expect(rec.size).toBe(0);

    expect(svc.getRecordingStatus()).toMatchObject({
      isRecording: true,
      isPaused: false,
      currentRecording: rec,
      totalRecordings: 0
    });
    expect(onStart).toHaveBeenCalledWith(rec);

    const saved = localStorage.getItem(`recording_${rec.id}`);
    expect(saved).toBeTruthy();
    const parsed = JSON.parse(saved!);
    expect(parsed.blob).toBeUndefined();
    expect(parsed.url).toBeUndefined();
  });

  test('startRecording prevents concurrent calls', async () => {
    const svc = new AudioService();
    await svc.startRecording('concurrent');
    await expect(svc.startRecording('concurrent')).rejects.toThrow('Recording is already in progress');
  });

  test('startRecording uses fallback mimeType when preferred unsupported', async () => {
    const spy = jest.spyOn(MockMediaRecorder, 'isTypeSupported').mockImplementation((type: string) => {
      if (type === 'audio/mpeg' || type === 'audio/mp4' || type === 'audio/wav') return false;
      if (type === 'audio/webm') return true;
      return false;
    });
    const svc = new AudioService();
    await svc.startRecording('sess-mime', 'm4a');
    expect(svc.getRecordingStatus().isRecording).toBe(true);
    spy.mockRestore();
  });

  test('pause and resume toggle flags and trigger callbacks', async () => {
    const svc = new AudioService();
    const onPause = jest.fn();
    const onResume = jest.fn();
    svc.setCallbacks({ onRecordingPause: onPause, onRecordingResume: onResume });

    await svc.startRecording('sess-2');
    svc.pauseRecording();
    expect(svc.getRecordingStatus().isPaused).toBe(true);
    expect(onPause).toHaveBeenCalled();

    svc.resumeRecording();
    expect(svc.getRecordingStatus().isPaused).toBe(false);
    expect(onResume).toHaveBeenCalled();
  });

  test('pauseRecording throws when not active or already paused', () => {
    const svc = new AudioService();
    expect(() => svc.pauseRecording()).toThrow('Cannot pause: no active recording or already paused');
  });

  test('resumeRecording throws when not paused', () => {
    const svc = new AudioService();
    expect(() => svc.resumeRecording()).toThrow('Cannot resume: no paused recording');
  });

  test('dataavailable updates chunks, notifies onDataAvailable, and persists size', async () => {
    const svc = new AudioService();
    const onData = jest.fn();
    svc.setCallbacks({ onDataAvailable: onData });

    const rec = await svc.startRecording('sess-3');
    const mr: any = (svc as any).mediaRecorder as MockMediaRecorder;

    mr.dispatchEvent('dataavailable', { data: new Blob([new Uint8Array([4,5,6,7])], { type: 'audio/wav' }) });

    const status = svc.getRecordingStatus();
    expect(status.currentRecording?.size).toBeGreaterThan(0);
    expect(onData).toHaveBeenCalled();

    const saved = localStorage.getItem(`recording_${rec.id}`);
    const parsed = JSON.parse(saved!);
    expect(parsed.size).toEqual(status.currentRecording!.size);
  });

  test('stopRecording finalizes blob/url/duration, adds to list, cleans up, persists, and calls onRecordingStop', async () => {
    const svc = new AudioService();
    const onStop = jest.fn();
    svc.setCallbacks({ onRecordingStop: onStop });

    const rec = await svc.startRecording('sess-4');
    const done = await svc.stopRecording();

    expect(done.id).toEqual(rec.id);
    expect(done.blob).toBeInstanceOf(Blob);
    expect(done.url).toMatch(/^blob:mock:\/\//);
    expect(typeof done.duration).toBe('number');

    expect(svc.getAllRecordings()).toHaveLength(1);
    expect(svc.getRecordingStatus()).toMatchObject({
      isRecording: false,
      isPaused: false,
      currentRecording: null,
      totalRecordings: 1
    });
    expect(onStop).toHaveBeenCalledWith(expect.objectContaining({ id: rec.id }));

    const list = JSON.parse(localStorage.getItem('audio_recordings') || '[]');
    expect(list).toContain(rec.id);
  });

  test('stopRecording rejects with no active recording', async () => {
    const svc = new AudioService();
    await expect(svc.stopRecording()).rejects.toThrow('No recording in progress');
  });

  test('getRecordingsBySession filters by sessionId', async () => {
    const svc = new AudioService();
    await svc.startRecording('s1');
    await svc.stopRecording();
    await svc.startRecording('s2');
    await svc.stopRecording();

    expect(svc.getRecordingsBySession('s1')).toHaveLength(1);
    expect(svc.getRecordingsBySession('s2')).toHaveLength(1);
    expect(svc.getRecordingsBySession('none')).toHaveLength(0);
  });

  test('deleteRecording removes item, revokes URL, updates storage', async () => {
    const svc = new AudioService();
    await svc.startRecording('sess-del');
    const { id } = await svc.stopRecording();
    const before = svc.getAllRecordings().length;

    const revokeSpy = jest.spyOn(URL, 'revokeObjectURL');
    svc.deleteRecording(id);

    expect(svc.getAllRecordings().length).toBe(before - 1);
    expect(revokeSpy).toHaveBeenCalled();
    expect(JSON.parse(localStorage.getItem('audio_recordings') || '[]')).not.toContain(id);
    expect(localStorage.getItem(`recording_${id}`)).toBeNull();
  });

  test('downloadRecording triggers anchor click when blob exists', async () => {
    const svc = new AudioService();
    await svc.startRecording('sess-dl');
    const rec = await svc.stopRecording();

    const { clicks } = installDomDownloadMocks();
    await svc.downloadRecording(rec.id);
    expect(clicks.length).toBe(1);
  });

  test('downloadRecording throws for missing recording or missing blob', async () => {
    const svc = new AudioService();
    await expect(svc.downloadRecording('missing')).rejects.toThrow('Recording not found or no data available');

    (svc as any).recordings.push({
      id: 'abc',
      sessionId: 's',
      startTime: new Date(),
      format: 'wav',
      size: 0
    });
    await expect(svc.downloadRecording('abc')).rejects.toThrow('Recording not found or no data available');
  });

  test('getRecordingStatus reflects lifecycle changes', async () => {
    const svc = new AudioService();
    expect(svc.getRecordingStatus()).toEqual({
      isRecording: false,
      isPaused: false,
      currentRecording: null,
      totalRecordings: 0
    });

    await svc.startRecording('sess-status');
    expect(svc.getRecordingStatus().isRecording).toBe(true);
    await svc.stopRecording();
    expect(svc.getRecordingStatus()).toMatchObject({ isRecording: false, isPaused: false, totalRecordings: 1 });
  });

  test('cleanup stops recorder, stops tracks, and resets state', async () => {
    const svc = new AudioService();
    await svc.startRecording('sess-clean');
    const stopSpy = jest.spyOn((svc as any).mediaRecorder as any, 'stop');
    const trackStopSpy = jest.fn();
    (svc as any).stream = {
      getTracks: () => [{ stop: trackStopSpy }]
    } as any;

    svc.cleanup();

    expect(stopSpy).toHaveBeenCalled();
    expect(trackStopSpy).toHaveBeenCalled();
    expect(svc.getRecordingStatus()).toEqual({
      isRecording: false,
      isPaused: false,
      currentRecording: null,
      totalRecordings: 0
    });
  });

  test('constructor loads persisted recordings and handles malformed entries', () => {
    const id1 = 'id1';
    const id2 = 'id2';
    localStorage.setItem('audio_recordings', JSON.stringify([id1, id2, 'id3']));
    localStorage.setItem(`recording_${id1}`, JSON.stringify({
      id: id1, sessionId: 's1', startTime: new Date().toISOString(), format: 'wav', size: 0
    }));
    localStorage.setItem(`recording_${id2}`, JSON.stringify({
      id: id2, sessionId: 's2', startTime: new Date().toISOString(), endTime: new Date().toISOString(), format: 'mp3', size: 10
    }));

    const svc = new AudioService();
    const recs = svc.getAllRecordings();
    expect(recs.length).toBe(2);
    expect(recs.find(r => r.id === id2)?.endTime).toBeInstanceOf(Date);
  });

  test('media recorder error event calls onError', async () => {
    const svc = new AudioService();
    const onErr = jest.fn();
    svc.setCallbacks({ onError: onErr });
    await svc.startRecording('sess-err');
    const mr: any = (svc as any).mediaRecorder;
    mr.dispatchEvent('error', { message: 'boom' });
    expect(onErr).toHaveBeenCalled();
  });

  test('stopRecording rejects and calls onError when finalization throws', async () => {
    const svc = new AudioService();
    const onErr = jest.fn();
    svc.setCallbacks({ onError: onErr });
    await svc.startRecording('sess-stop-err');

    // Force error when creating Blob
    (svc as any).audioChunks = [null as unknown as Blob];

    await expect(svc.stopRecording()).rejects.toThrow();
    expect(onErr).toHaveBeenCalled();
  });
});