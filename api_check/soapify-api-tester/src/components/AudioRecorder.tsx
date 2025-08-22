import React from 'react';
import styled from 'styled-components';
import { TestSession, AudioRecording } from '../types';
import AudioService from '../services/audioService';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
`;

const Card = styled.div`
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 32px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h1`
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 16px 0;
`;

interface AudioRecorderProps {
  audioService: AudioService | null;
  currentSession: TestSession | null;
  onRecordingUpdate: (recording: AudioRecording) => void;
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({
  audioService,
  currentSession,
  onRecordingUpdate
}) => {
  return (
    <Container>
      <Card>
        <Title>Audio Recorder</Title>
        <p>Audio recording controls and history will be displayed here.</p>
        <p>Current session: {currentSession?.name || 'None'}</p>
      </Card>
    </Container>
  );
};

export default AudioRecorder;