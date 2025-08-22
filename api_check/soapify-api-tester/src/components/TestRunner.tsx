import React from 'react';
import styled from 'styled-components';
import { TestSession, ApiEndpoint } from '../types';
import ApiService from '../services/apiService';
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

interface TestRunnerProps {
  session: TestSession;
  endpoints: ApiEndpoint[];
  apiService: ApiService | null;
  audioService: AudioService | null;
  onSessionUpdate: (session: TestSession) => void;
}

const TestRunner: React.FC<TestRunnerProps> = ({
  session,
  endpoints,
  apiService,
  audioService,
  onSessionUpdate
}) => {
  return (
    <Container>
      <Card>
        <Title>Test Runner</Title>
        <p>Test runner functionality will be implemented here.</p>
        <p>Session: {session.name}</p>
        <p>Total endpoints to test: {endpoints.length}</p>
      </Card>
    </Container>
  );
};

export default TestRunner;