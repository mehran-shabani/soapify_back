import React from 'react';
import styled from 'styled-components';
import { TestSession } from '../types';

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

interface ResultsProps {
  sessions: TestSession[];
  onSessionSelect: (session: TestSession) => void;
}

const Results: React.FC<ResultsProps> = ({ sessions, onSessionSelect }) => {
  return (
    <Container>
      <Card>
        <Title>Test Results</Title>
        <p>Test results and analytics will be displayed here.</p>
        <p>Available sessions: {sessions.length}</p>
      </Card>
    </Container>
  );
};

export default Results;