import React, { useState, useRef } from 'react';
import styled from 'styled-components';
import { ReactMic } from 'react-mic';
import { toast } from 'react-toastify';
import { voiceService, sttService } from '../services/apiService';

// Create event emitter for error handling
class ErrorEmitter extends EventTarget {}
export const errorEmitter = new ErrorEmitter();

const Container = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const Title = styled.h2`
  margin-bottom: 20px;
  color: #2c3e50;
`;

const RecorderContainer = styled.div`
  margin: 20px 0;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  text-align: center;
`;

const Button = styled.button`
  background-color: ${props => props.recording ? '#e74c3c' : '#3498db'};
  color: white;
  border: none;
  padding: 12px 24px;
  margin: 5px;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const InfoCard = styled.div`
  background: #ecf0f1;
  padding: 15px;
  border-radius: 8px;
  margin: 10px 0;
`;

const Metric = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #bdc3c7;

  &:last-child {
    border-bottom: none;
  }
`;

const Label = styled.span`
  font-weight: 600;
  color: #34495e;
`;

const Value = styled.span`
  color: ${props => props.success ? '#27ae60' : props.error ? '#e74c3c' : '#3498db'};
`;

const TranscriptionBox = styled.div`
  background: #fff;
  border: 2px solid #ecf0f1;
  border-radius: 8px;
  padding: 15px;
  margin: 15px 0;
  min-height: 80px;
  text-align: right;
`;

/**
 * VoiceRecorder component: provides UI and logic to record audio, play it back, upload it, and request transcription.
 *
 * Renders recording controls (start/stop), playback, and upload buttons; displays audio file statistics, upload results,
 * and transcription results. Uses React state to track recording, upload, and transcription status.
 *
 * Side effects:
 * - Shows user-facing toast notifications for recording/upload/transcription progress and errors.
 * - Calls voiceService.uploadAudio to upload recorded audio and sttService.transcribe to transcribe uploaded audio.
 * - Emits diagnostic error events via the exported errorEmitter on upload failures.
 *
 * @returns {JSX.Element} The recorder UI.
 */
function VoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [transcriptionResult, setTranscriptionResult] = useState(null);
  const [audioStats, setAudioStats] = useState(null);

  const startRecording = () => {
    setIsRecording(true);
    setRecordedBlob(null);
    setUploadResult(null);
    setTranscriptionResult(null);
    toast.info('شروع ضبط صدا...');
  };

  const stopRecording = () => {
    setIsRecording(false);
    toast.info('ضبط صدا متوقف شد');
  };

  const onData = (recordedData) => {
    // This is called frequently during recording
    // console.log('Recording data chunk...');
  };

  const onStop = (recordedBlob) => {
    setRecordedBlob(recordedBlob);
    
    // Calculate audio stats
    const stats = {
      size: (recordedBlob.blob.size / 1024).toFixed(2), // KB
      duration: recordedBlob.stopTime - recordedBlob.startTime, // ms
      format: recordedBlob.blob.type
    };
    setAudioStats(stats);
  };

  const uploadRecording = async () => {
    if (!recordedBlob) {
      toast.error('ابتدا صدایی ضبط کنید');
      return;
    }

    setIsUploading(true);
    const startTime = Date.now();

    try {
      // Upload audio
      const uploadResponse = await voiceService.uploadAudio(recordedBlob.blob, {
        title: `تست ضبط ${new Date().toLocaleTimeString('fa-IR')}`,
        description: 'ضبط شده از طریق برنامه تست API'
      });

      const uploadTime = Date.now() - startTime;
      
      setUploadResult({
        ...uploadResponse,
        uploadTime,
        uploadSpeed: ((recordedBlob.blob.size / 1024) / (uploadTime / 1000)).toFixed(2) // KB/s
      });

      toast.success('آپلود با موفقیت انجام شد');

      // If upload successful, try transcription
      if (uploadResponse.success && uploadResponse.data?.audio_url) {
        toast.info('در حال تبدیل گفتار به متن...');
        
        const sttStartTime = Date.now();
        const sttResponse = await sttService.transcribe(uploadResponse.data.audio_url);
        const sttTime = Date.now() - sttStartTime;

        setTranscriptionResult({
          ...sttResponse,
          processingTime: sttTime
        });

        if (sttResponse.success) {
          toast.success('تبدیل گفتار به متن انجام شد');
        }
      }

    } catch (error) {
      toast.error(`خطا در آپلود: ${error.message}`);
      setUploadResult({
        success: false,
        error: error.message,
        responseTime: Date.now() - startTime
      });
      
      // Emit error for diagnostic panel
      errorEmitter.dispatchEvent(new CustomEvent('error', {
        detail: {
          error,
          endpoint: 'voice/upload',
          timestamp: new Date().toISOString()
        }
      }));
    } finally {
      setIsUploading(false);
    }
  };

  const playRecording = () => {
    if (recordedBlob) {
      const audio = new Audio(recordedBlob.blobURL);
      audio.play();
    }
  };

  return (
    <Container>
      <Title>تست ضبط و آپلود صدا</Title>

      <RecorderContainer>
        <ReactMic
          record={isRecording}
          className="sound-wave"
          onStop={onStop}
          onData={onData}
          strokeColor="#3498db"
          backgroundColor="#ecf0f1"
          mimeType="audio/wav"
        />

        <div style={{ marginTop: '20px' }}>
          <Button onClick={isRecording ? stopRecording : startRecording} recording={isRecording}>
            {isRecording ? 'توقف ضبط' : 'شروع ضبط'}
          </Button>

          {recordedBlob && (
            <>
              <Button onClick={playRecording}>
                پخش صدا
              </Button>
              <Button onClick={uploadRecording} disabled={isUploading}>
                {isUploading ? 'در حال آپلود...' : 'آپلود صدا'}
              </Button>
            </>
          )}
        </div>
      </RecorderContainer>

      {audioStats && (
        <InfoCard>
          <h3>مشخصات فایل صوتی</h3>
          <Metric>
            <Label>حجم فایل:</Label>
            <Value>{audioStats.size} KB</Value>
          </Metric>
          <Metric>
            <Label>مدت زمان:</Label>
            <Value>{(audioStats.duration / 1000).toFixed(1)} ثانیه</Value>
          </Metric>
          <Metric>
            <Label>فرمت:</Label>
            <Value>{audioStats.format}</Value>
          </Metric>
        </InfoCard>
      )}

      {uploadResult && (
        <InfoCard>
          <h3>نتیجه آپلود</h3>
          <Metric>
            <Label>وضعیت:</Label>
            <Value success={uploadResult.success} error={!uploadResult.success}>
              {uploadResult.success ? 'موفق' : 'ناموفق'}
            </Value>
          </Metric>
          <Metric>
            <Label>زمان پاسخ:</Label>
            <Value>{uploadResult.responseTime} ms</Value>
          </Metric>
          <Metric>
            <Label>زمان آپلود:</Label>
            <Value>{uploadResult.uploadTime} ms</Value>
          </Metric>
          <Metric>
            <Label>سرعت آپلود:</Label>
            <Value>{uploadResult.uploadSpeed} KB/s</Value>
          </Metric>
          {uploadResult.error && (
            <Metric>
              <Label>خطا:</Label>
              <Value error>{uploadResult.error}</Value>
            </Metric>
          )}
        </InfoCard>
      )}

      {transcriptionResult && (
        <>
          <InfoCard>
            <h3>نتیجه تبدیل گفتار به متن</h3>
            <Metric>
              <Label>وضعیت:</Label>
              <Value success={transcriptionResult.success} error={!transcriptionResult.success}>
                {transcriptionResult.success ? 'موفق' : 'ناموفق'}
              </Value>
            </Metric>
            <Metric>
              <Label>زمان پردازش:</Label>
              <Value>{transcriptionResult.processingTime} ms</Value>
            </Metric>
          </InfoCard>

          {transcriptionResult.success && transcriptionResult.data?.transcription && (
            <TranscriptionBox>
              <h4>متن تشخیص داده شده:</h4>
              <p>{transcriptionResult.data.transcription}</p>
            </TranscriptionBox>
          )}
        </>
      )}
    </Container>
  );
}

export default VoiceRecorder;