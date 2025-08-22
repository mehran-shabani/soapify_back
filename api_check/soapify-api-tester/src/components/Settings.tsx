import React from 'react';
import styled from 'styled-components';
import { TestConfig, ApiEndpoint } from '../types';

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

interface SettingsProps {
  config: TestConfig;
  onConfigUpdate: (config: TestConfig) => void;
  endpoints: ApiEndpoint[];
}

const Settings: React.FC<SettingsProps> = ({ config, onConfigUpdate, endpoints }) => {
  return (
    <Container>
      <Card>
        <Title>Settings</Title>
        <p>Application settings and configuration will be displayed here.</p>
        <p>Base URL: {config.baseUrl}</p>
        <p>Audio Recording: {config.enableAudioRecording ? 'Enabled' : 'Disabled'}</p>
      </Card>
    </Container>
  );
};

export default Settings;