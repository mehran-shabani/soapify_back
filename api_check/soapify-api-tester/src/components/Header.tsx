import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { Play, Pause, Square, Mic, Activity, Settings, Home, TestTube, BarChart3, Volume2 } from 'lucide-react';
import { TestSession, AudioRecording } from '../types';
import AudioService from '../services/audioService';
import { formatDuration } from '../utils/helpers';

const HeaderContainer = styled.header`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0 20px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
`;

const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 700;
  font-size: 1.5rem;
  color: #4f46e5;
  text-decoration: none;
`;

const LogoIcon = styled.div`
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
`;

const Navigation = styled.nav`
  display: flex;
  gap: 8px;
`;

const NavLink = styled(Link)<{ $active?: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 12px;
  text-decoration: none;
  color: ${props => props.$active ? '#4f46e5' : '#64748b'};
  background: ${props => props.$active ? 'rgba(79, 70, 229, 0.1)' : 'transparent'};
  font-weight: ${props => props.$active ? '600' : '500'};
  transition: all 0.2s ease;

  &:hover {
    background: rgba(79, 70, 229, 0.1);
    color: #4f46e5;
  }

  svg {
    width: 18px;
    height: 18px;
  }
`;

const AudioControls = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.1);
`;

const AudioButton = styled.button<{ $variant?: 'primary' | 'danger' | 'secondary' }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  background: ${props => {
    switch (props.$variant) {
      case 'primary': return '#10b981';
      case 'danger': return '#ef4444';
      case 'secondary': return '#6b7280';
      default: return '#f3f4f6';
    }
  }};
  
  color: ${props => props.$variant ? 'white' : '#374151'};

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &:active {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }

  svg {
    width: 20px;
    height: 20px;
  }
`;

const AudioStatus = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 120px;
`;

const AudioStatusText = styled.div`
  font-size: 0.75rem;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const AudioTimer = styled.div`
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  font-family: 'JetBrains Mono', monospace;
`;

const SessionInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 12px;
  border: 1px solid rgba(16, 185, 129, 0.2);
`;

const SessionName = styled.div`
  font-size: 0.875rem;
  font-weight: 600;
  color: #065f46;
`;

const SessionStatus = styled.div<{ $status: string }>`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  color: ${props => {
    switch (props.$status) {
      case 'running': return '#059669';
      case 'completed': return '#0d9488';
      case 'paused': return '#d97706';
      case 'failed': return '#dc2626';
      default: return '#6b7280';
    }
  }};

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: ${props => props.$status === 'running' ? 'pulse 2s infinite' : 'none'};
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`;

interface HeaderProps {
  currentSession: TestSession | null;
  audioService: AudioService | null;
  onAudioRecording: (recording: AudioRecording) => void;
}

const Header: React.FC<HeaderProps> = ({ currentSession, audioService, onAudioRecording }) => {
  const location = useLocation();
  const [audioStatus, setAudioStatus] = useState<{
    isRecording: boolean;
    isPaused: boolean;
    currentRecording: AudioRecording | null;
    totalRecordings: number;
  }>({
    isRecording: false,
    isPaused: false,
    currentRecording: null,
    totalRecordings: 0
  });
  const [recordingDuration, setRecordingDuration] = useState(0);

  // Update audio status
  useEffect(() => {
    if (audioService) {
      const updateStatus = () => {
        const status = audioService.getRecordingStatus();
        setAudioStatus(status);
      };

      // Set up audio service callbacks
      audioService.setCallbacks({
        onRecordingStart: (recording) => {
          updateStatus();
          onAudioRecording(recording);
        },
        onRecordingStop: (recording) => {
          updateStatus();
          onAudioRecording(recording);
          setRecordingDuration(0);
        },
        onRecordingPause: (recording) => {
          updateStatus();
          onAudioRecording(recording);
        },
        onRecordingResume: (recording) => {
          updateStatus();
          onAudioRecording(recording);
        },
        onError: (error) => {
          console.error('Audio recording error:', error);
          updateStatus();
        }
      });

      updateStatus();
    }
  }, [audioService, onAudioRecording]);

  // Update recording duration timer
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (audioStatus.isRecording && !audioStatus.isPaused && audioStatus.currentRecording) {
      interval = setInterval(() => {
        const startTime = (audioStatus.currentRecording as any).startTime;
        const duration = Date.now() - new Date(startTime).getTime();
        setRecordingDuration(duration);
      }, 100);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [audioStatus.isRecording, audioStatus.isPaused, audioStatus.currentRecording]);

  const handleStartRecording = async () => {
    if (!audioService) return;

    try {
      const sessionId = currentSession?.id || 'default';
      await audioService.startRecording(sessionId, 'wav');
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  };

  const handleStopRecording = async () => {
    if (!audioService) return;

    try {
      await audioService.stopRecording();
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  };

  const handlePauseRecording = () => {
    if (!audioService) return;

    try {
      if (audioStatus.isPaused) {
        audioService.resumeRecording();
      } else {
        audioService.pauseRecording();
      }
    } catch (error) {
      console.error('Failed to pause/resume recording:', error);
    }
  };

  const getNavLinks = () => [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/test', label: 'Test Runner', icon: TestTube },
    { path: '/results', label: 'Results', icon: BarChart3 },
    { path: '/audio', label: 'Audio', icon: Volume2 },
    { path: '/settings', label: 'Settings', icon: Settings }
  ];

  return (
    <HeaderContainer>
      <Logo as={Link} to="/">
        <LogoIcon>
          <Activity />
        </LogoIcon>
        Soapify API Tester
      </Logo>

      <Navigation>
        {getNavLinks().map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            $active={location.pathname === path}
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </Navigation>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Session Info */}
        {currentSession && (
          <SessionInfo>
            <SessionName>{currentSession.name}</SessionName>
            <SessionStatus $status={currentSession.status}>
              {currentSession.status}
            </SessionStatus>
          </SessionInfo>
        )}

        {/* Audio Controls */}
        <AudioControls>
          <AudioStatus>
            <AudioStatusText>
              {audioStatus.isRecording 
                ? (audioStatus.isPaused ? 'Paused' : 'Recording') 
                : 'Ready'
              }
            </AudioStatusText>
            <AudioTimer>
              {audioStatus.isRecording ? formatDuration(recordingDuration) : '00:00'}
            </AudioTimer>
          </AudioStatus>

          {!audioStatus.isRecording ? (
            <AudioButton
              $variant="primary"
              onClick={handleStartRecording}
              title="Start Recording"
            >
              <Mic />
            </AudioButton>
          ) : (
            <>
              <AudioButton
                $variant="secondary"
                onClick={handlePauseRecording}
                title={audioStatus.isPaused ? "Resume Recording" : "Pause Recording"}
              >
                {audioStatus.isPaused ? <Play /> : <Pause />}
              </AudioButton>
              <AudioButton
                $variant="danger"
                onClick={handleStopRecording}
                title="Stop Recording"
              >
                <Square />
              </AudioButton>
            </>
          )}
        </AudioControls>
      </div>
    </HeaderContainer>
  );
};

export default Header;