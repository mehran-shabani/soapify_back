import React from 'react';
import styled, { keyframes } from 'styled-components';
import { Activity } from 'lucide-react';

const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

const LoadingContainer = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
`;

const LoadingContent = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  text-align: center;
`;

const LogoContainer = styled.div`
  position: relative;
  width: 80px;
  height: 80px;
`;

const LogoIcon = styled.div`
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  animation: ${pulse} 2s infinite;

  svg {
    width: 40px;
    height: 40px;
  }
`;

const LoadingSpinner = styled.div`
  position: absolute;
  top: -8px;
  left: -8px;
  right: -8px;
  bottom: -8px;
  border: 2px solid transparent;
  border-top: 2px solid rgba(255, 255, 255, 0.8);
  border-right: 2px solid rgba(255, 255, 255, 0.4);
  border-radius: 24px;
  animation: ${spin} 1s linear infinite;
`;

const LoadingTitle = styled.h1`
  font-size: 2rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(45deg, #ffffff, #e0e7ff);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;

const LoadingSubtitle = styled.p`
  font-size: 1.125rem;
  margin: 0;
  opacity: 0.8;
  animation: ${pulse} 3s infinite;
`;

const LoadingSteps = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
`;

const LoadingStep = styled.div`
  font-size: 0.875rem;
  opacity: 0.6;
  display: flex;
  align-items: center;
  gap: 8px;

  &::before {
    content: '•';
    color: rgba(255, 255, 255, 0.8);
    font-weight: bold;
  }
`;

const LoadingScreen: React.FC = () => {
  return (
    <LoadingContainer>
      <LoadingContent>
        <LogoContainer>
          <LogoIcon>
            <Activity />
          </LogoIcon>
          <LoadingSpinner />
        </LogoContainer>

        <LoadingTitle>Soapify API Tester</LoadingTitle>
        
        <LoadingSubtitle>Initializing application...</LoadingSubtitle>

        <LoadingSteps>
          <LoadingStep>Loading API endpoints</LoadingStep>
          <LoadingStep>Initializing services</LoadingStep>
          <LoadingStep>Checking for previous sessions</LoadingStep>
          <LoadingStep>Setting up audio recording</LoadingStep>
        </LoadingSteps>
      </LoadingContent>
    </LoadingContainer>
  );
};

export default LoadingScreen;