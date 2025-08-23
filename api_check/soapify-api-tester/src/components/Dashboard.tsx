import React, { useState } from 'react';
import styled from 'styled-components';
import { Play, Settings, BarChart3, CheckCircle } from 'lucide-react';
import { ApiEndpoint, TestConfig, TestSession } from '../types';

const DashboardContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
`;

const WelcomeSection = styled.div`
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 32px;
  text-align: center;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
`;

const WelcomeTitle = styled.h1`
  font-size: 2.5rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 16px 0;
`;

const WelcomeSubtitle = styled.p`
  font-size: 1.25rem;
  color: #64748b;
  margin: 0 0 32px 0;
  line-height: 1.6;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
`;

const StatCard = styled.div`
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
`;

const StatNumber = styled.div`
  font-size: 2rem;
  font-weight: 700;
  color: #4f46e5;
  margin-bottom: 8px;
`;

const StatLabel = styled.div`
  font-size: 0.875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
`;

const ActionButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 16px 32px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1.125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  margin: 0 8px;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(79, 70, 229, 0.3);
  }

  &:active {
    transform: translateY(0);
  }

  svg {
    width: 20px;
    height: 20px;
  }
`;

const QuickStartSection = styled.div`
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 32px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
`;

const SectionTitle = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 24px 0;
`;

const QuickStartGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
`;

const QuickStartCard = styled.div`
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  background: white;
  transition: all 0.2s ease;

  &:hover {
    border-color: #4f46e5;
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.1);
  }
`;

const CardTitle = styled.h3`
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const CardDescription = styled.p`
  color: #64748b;
  margin: 0 0 16px 0;
  line-height: 1.6;
`;

const CardButton = styled.button`
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 20px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;

  &:hover {
    background: #4338ca;
  }
`;

interface DashboardProps {
  endpoints: ApiEndpoint[];
  currentSession: TestSession | null;
  config: TestConfig;
  onNewSession: (name: string, selectedEndpoints: ApiEndpoint[]) => TestSession;
  onConfigUpdate: (config: TestConfig) => void;
}

const Dashboard: React.FC<DashboardProps> = ({
  endpoints,
  currentSession,
  config,
  onNewSession,
  onConfigUpdate
}) => {
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  const handleQuickStart = () => {
    setIsCreatingSession(true);
    try {
      const session = onNewSession('Quick Test Session', endpoints.slice(0, 10));
      // Navigate to test runner would happen here
      console.log('Created session:', session);
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsCreatingSession(false);
    }
  };

  const getEndpointsByCategory = () => {
    const categories: Record<string, number> = {};
    endpoints.forEach(endpoint => {
      categories[endpoint.category] = (categories[endpoint.category] || 0) + 1;
    });
    return categories;
  };

  const categories = getEndpointsByCategory();

  return (
    <DashboardContainer>
      <WelcomeSection>
        <WelcomeTitle>Welcome to Soapify API Tester</WelcomeTitle>
        <WelcomeSubtitle>
          Comprehensive API testing tool with real-time audio recording and advanced analytics
        </WelcomeSubtitle>

        <StatsGrid>
          <StatCard>
            <StatNumber>{endpoints.length}</StatNumber>
            <StatLabel>Total Endpoints</StatLabel>
          </StatCard>
          <StatCard>
            <StatNumber>{Object.keys(categories).length}</StatNumber>
            <StatLabel>Categories</StatLabel>
          </StatCard>
          <StatCard>
            <StatNumber>{currentSession ? 1 : 0}</StatNumber>
            <StatLabel>Active Sessions</StatLabel>
          </StatCard>
          <StatCard>
            <StatNumber>{config.enableAudioRecording ? 'ON' : 'OFF'}</StatNumber>
            <StatLabel>Audio Recording</StatLabel>
          </StatCard>
        </StatsGrid>

        <div>
          <ActionButton onClick={handleQuickStart} disabled={isCreatingSession}>
            <Play />
            {isCreatingSession ? 'Creating Session...' : 'Quick Start Test'}
          </ActionButton>
          <ActionButton onClick={() => console.log('Settings')}>
            <Settings />
            Configure Settings
          </ActionButton>
        </div>
      </WelcomeSection>

      <QuickStartSection>
        <SectionTitle>Quick Actions</SectionTitle>
        
        <QuickStartGrid>
          <QuickStartCard>
            <CardTitle>
              <Play />
              Run All Tests
            </CardTitle>
            <CardDescription>
              Execute all {endpoints.length} API endpoints with current configuration. 
              Includes timing measurements and response validation.
            </CardDescription>
            <CardButton onClick={handleQuickStart}>
              Start Full Test Suite
            </CardButton>
          </QuickStartCard>

          <QuickStartCard>
            <CardTitle>
              <CheckCircle />
              Custom Test Selection
            </CardTitle>
            <CardDescription>
              Choose specific endpoints or categories to test. 
              Perfect for targeted testing of specific functionality.
            </CardDescription>
            <CardButton onClick={() => console.log('Custom selection')}>
              Select Endpoints
            </CardButton>
          </QuickStartCard>

          <QuickStartCard>
            <CardTitle>
              <BarChart3 />
              View Previous Results
            </CardTitle>
            <CardDescription>
              Review past test sessions, analyze performance trends, 
              and export detailed reports.
            </CardDescription>
            <CardButton onClick={() => console.log('Results')}>
              View Results
            </CardButton>
          </QuickStartCard>
        </QuickStartGrid>
      </QuickStartSection>

      {Object.keys(categories).length > 0 && (
        <QuickStartSection>
          <SectionTitle>API Categories</SectionTitle>
          
          <QuickStartGrid>
            {Object.entries(categories).map(([category, count]) => (
              <QuickStartCard key={category}>
                <CardTitle>
                  <CheckCircle />
                  {category}
                </CardTitle>
                <CardDescription>
                  {count} endpoint{count !== 1 ? 's' : ''} available for testing
                </CardDescription>
                <CardButton onClick={() => console.log(`Test ${category}`)}>
                  Test {category}
                </CardButton>
              </QuickStartCard>
            ))}
          </QuickStartGrid>
        </QuickStartSection>
      )}
    </DashboardContainer>
  );
};

export default Dashboard;