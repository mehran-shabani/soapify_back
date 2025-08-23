import { AudioRecording } from '../types';
import { generateId } from '../utils/helpers';

export class AudioService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private currentRecording: AudioRecording | null = null;
  private recordings: AudioRecording[] = [];
  private isRecording = false;
  private isPaused = false;

  // Event callbacks
  private onRecordingStart?: (recording: AudioRecording) => void;
  private onRecordingStop?: (recording: AudioRecording) => void;
  private onRecordingPause?: (recording: AudioRecording) => void;
  private onRecordingResume?: (recording: AudioRecording) => void;
  private onDataAvailable?: (chunk: Blob) => void;
  private onError?: (error: Error) => void;

  constructor() {
    this.loadRecordingsFromStorage();
  }

  // Set event callbacks
  setCallbacks(callbacks: {
    onRecordingStart?: (recording: AudioRecording) => void;
    onRecordingStop?: (recording: AudioRecording) => void;
    onRecordingPause?: (recording: AudioRecording) => void;
    onRecordingResume?: (recording: AudioRecording) => void;
    onDataAvailable?: (chunk: Blob) => void;
    onError?: (error: Error) => void;
  }) {
    this.onRecordingStart = callbacks.onRecordingStart;
    this.onRecordingStop = callbacks.onRecordingStop;
    this.onRecordingPause = callbacks.onRecordingPause;
    this.onRecordingResume = callbacks.onRecordingResume;
    this.onDataAvailable = callbacks.onDataAvailable;
    this.onError = callbacks.onError;
  }

  async startRecording(sessionId: string, format: 'wav' | 'mp3' | 'm4a' = 'wav'): Promise<AudioRecording> {
    try {
      if (this.isRecording) {
        throw new Error('Recording is already in progress');
      }

      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      // Determine MIME type based on format and browser support
      const mimeType = this.getMimeType(format);
      
      // Create MediaRecorder with fallback options
      const options: MediaRecorderOptions = {};
      if (MediaRecorder.isTypeSupported(mimeType)) {
        options.mimeType = mimeType;
      } else {
        // Fallback to browser default or webm
        if (MediaRecorder.isTypeSupported('audio/webm')) {
          options.mimeType = 'audio/webm';
        }
        console.warn(`MIME type ${mimeType} not supported, using browser default`);
      }
      
      this.mediaRecorder = new MediaRecorder(this.stream, options);

      // Create recording object
      this.currentRecording = {
        id: generateId(),
        sessionId,
        startTime: new Date(),
        format,
        size: 0
      };

      // Reset audio chunks
      this.audioChunks = [];

      // Set up event listeners
      this.setupMediaRecorderEvents();

      // Start recording
      this.mediaRecorder.start(1000); // Collect data every second
      this.isRecording = true;
      this.isPaused = false;

      // Save to storage
      this.saveRecordingToStorage(this.currentRecording);

      // Trigger callback
      if (this.onRecordingStart) {
        this.onRecordingStart(this.currentRecording);
      }

      return this.currentRecording;

    } catch (error) {
      const errorObj = error instanceof Error ? error : new Error('Failed to start recording');
      if (this.onError) {
        this.onError(errorObj);
      }
      throw errorObj;
    }
  }

  stopRecording(): Promise<AudioRecording> {
    return new Promise((resolve, reject) => {
      if (!this.isRecording || !this.mediaRecorder || !this.currentRecording) {
        reject(new Error('No recording in progress'));
        return;
      }

      const recording = this.currentRecording;

      // Set up one-time event listener for stop
      this.mediaRecorder.addEventListener('stop', () => {
        try {
          // Create final blob
          const blob = new Blob(this.audioChunks, { 
            type: this.getMimeType(recording.format) 
          });

          // Update recording with final data
          recording.endTime = new Date();
          recording.duration = recording.endTime.getTime() - recording.startTime.getTime();
          recording.blob = blob;
          recording.size = blob.size;
          recording.url = URL.createObjectURL(blob);

          // Add to recordings list
          this.recordings.push(recording);

          // Clean up
          this.cleanup();

          // Save to storage
          this.saveRecordingToStorage(recording);
          this.saveRecordingsToStorage();

          // Trigger callback
          if (this.onRecordingStop) {
            this.onRecordingStop(recording);
          }

          resolve(recording);

        } catch (error) {
          const errorObj = error instanceof Error ? error : new Error('Failed to stop recording');
          if (this.onError) {
            this.onError(errorObj);
          }
          reject(errorObj);
        }
      }, { once: true });

      // Stop recording
      this.mediaRecorder.stop();
      this.isRecording = false;
      this.isPaused = false;
    });
  }

  pauseRecording(): void {
    if (!this.isRecording || !this.mediaRecorder || this.isPaused) {
      throw new Error('Cannot pause: no active recording or already paused');
    }

    this.mediaRecorder.pause();
    this.isPaused = true;

    if (this.onRecordingPause && this.currentRecording) {
      this.onRecordingPause(this.currentRecording);
    }
  }

  resumeRecording(): void {
    if (!this.isRecording || !this.mediaRecorder || !this.isPaused) {
      throw new Error('Cannot resume: no paused recording');
    }

    this.mediaRecorder.resume();
    this.isPaused = false;

    if (this.onRecordingResume && this.currentRecording) {
      this.onRecordingResume(this.currentRecording);
    }
  }

  getCurrentRecording(): AudioRecording | null {
    return this.currentRecording;
  }

  getAllRecordings(): AudioRecording[] {
    return [...this.recordings];
  }

  getRecordingsBySession(sessionId: string): AudioRecording[] {
    return this.recordings.filter(recording => recording.sessionId === sessionId);
  }

  deleteRecording(recordingId: string): void {
    const index = this.recordings.findIndex(r => r.id === recordingId);
    if (index !== -1) {
      const recording = this.recordings[index];
      
      // Revoke object URL to free memory
      if (recording.url) {
        URL.revokeObjectURL(recording.url);
      }

      // Remove from array
      this.recordings.splice(index, 1);

      // Update storage
      this.saveRecordingsToStorage();
      this.removeRecordingFromStorage(recordingId);
    }
  }

  async downloadRecording(recordingId: string): Promise<void> {
    const recording = this.recordings.find(r => r.id === recordingId);
    if (!recording || !recording.blob) {
      throw new Error('Recording not found or no data available');
    }

    const url = recording.url || URL.createObjectURL(recording.blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `recording_${recording.id}_${recording.startTime.toISOString()}.${recording.format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  getRecordingStatus(): {
    isRecording: boolean;
    isPaused: boolean;
    currentRecording: AudioRecording | null;
    totalRecordings: number;
  } {
    return {
      isRecording: this.isRecording,
      isPaused: this.isPaused,
      currentRecording: this.currentRecording,
      totalRecordings: this.recordings.length
    };
  }

  // Cleanup method for component unmounting
  cleanup(): void {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    this.mediaRecorder = null;
    this.currentRecording = null;
    this.isRecording = false;
    this.isPaused = false;
    this.audioChunks = [];
  }

  private setupMediaRecorderEvents(): void {
    if (!this.mediaRecorder) return;

    this.mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data && event.data.size > 0) {
        this.audioChunks.push(event.data);
        
        if (this.onDataAvailable) {
          this.onDataAvailable(event.data);
        }

        // Update current recording size
        if (this.currentRecording) {
          this.currentRecording.size = this.audioChunks.reduce((total, chunk) => total + chunk.size, 0);
          this.saveRecordingToStorage(this.currentRecording);
        }
      }
    });

    this.mediaRecorder.addEventListener('error', (event) => {
      const error = new Error(`MediaRecorder error: ${event}`);
      if (this.onError) {
        this.onError(error);
      }
    });
  }

  private getMimeType(format: string): string {
    switch (format) {
      case 'mp3':
        return 'audio/mpeg';
      case 'm4a':
        return 'audio/mp4';
      case 'wav':
      default:
        return 'audio/wav';
    }
  }

  private saveRecordingToStorage(recording: AudioRecording): void {
    try {
      const recordingData = {
        ...recording,
        blob: undefined, // Don't store blob in localStorage
        url: undefined   // Don't store URL in localStorage
      };
      localStorage.setItem(`recording_${recording.id}`, JSON.stringify(recordingData));
    } catch (error) {
      console.warn('Failed to save recording to storage:', error);
    }
  }

  private saveRecordingsToStorage(): void {
    try {
      const recordingIds = this.recordings.map(r => r.id);
      localStorage.setItem('audio_recordings', JSON.stringify(recordingIds));
    } catch (error) {
      console.warn('Failed to save recordings list to storage:', error);
    }
  }

  private loadRecordingsFromStorage(): void {
    try {
      const recordingIds = JSON.parse(localStorage.getItem('audio_recordings') || '[]');
      
      for (const id of recordingIds) {
        const recordingData = localStorage.getItem(`recording_${id}`);
        if (recordingData) {
          const recording: AudioRecording = {
            ...JSON.parse(recordingData),
            startTime: new Date(JSON.parse(recordingData).startTime),
            endTime: JSON.parse(recordingData).endTime ? new Date(JSON.parse(recordingData).endTime) : undefined
          };
          this.recordings.push(recording);
        }
      }
    } catch (error) {
      console.warn('Failed to load recordings from storage:', error);
    }
  }

  private removeRecordingFromStorage(recordingId: string): void {
    try {
      localStorage.removeItem(`recording_${recordingId}`);
    } catch (error) {
      console.warn('Failed to remove recording from storage:', error);
    }
  }
}

export default AudioService;