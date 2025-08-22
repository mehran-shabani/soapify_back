import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import styled from 'styled-components';

// Components
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import TestRunner from './components/TestRunner';
import Results from './components/Results';
import AudioRecorder from './components/AudioRecorder';
import Settings from './components/Settings';
import LoadingScreen from './components/LoadingScreen';

// Services and utilities
import ApiService from './services/apiService';
import AudioService from './services/audioService';
import { ApiEndpoint, TestConfig, TestSession, AudioRecording } from './types';
import { generateId, loadResumeData } from './utils/helpers';

// Import API endpoints
import apiEndpoints from './data/api_endpoints.json';

// Styles
import 'react-toastify/dist/ReactToastify.css';

const AppContainer = styled.div`
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
`;

const MainContent = styled.main`
  min-height: calc(100vh - 80px);
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
`;

const GlobalStyle = styled.div`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #f8fafc;
    color: #1a202c;
    line-height: 1.6;
  }

  .toast-container {
    .Toastify__toast {
      border-radius: 12px;
      font-family: 'Inter', sans-serif;
    }
  }
`;

function App() {
  // Global state
  const [isLoading, setIsLoading] = useState(true);
  const [currentSession, setCurrentSession] = useState<TestSession | null>(null);
  const [apiService, setApiService] = useState<ApiService | null>(null);
  const [audioService, setAudioService] = useState<AudioService | null>(null);
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([]);
  const [config, setConfig] = useState<TestConfig>({
    baseUrl: 'https://django-m.chbk.app',
    timeout: 30000,
    retries: 1,
    concurrency: 1,
    enableAudioRecording: true,
    audioFormat: 'wav',
    testMethods: ['GET', 'POST', 'PUT', 'DELETE'],
    validateResponses: true,
    saveResults: true,
    resumeOnFailure: true
  });

  // Initialize services and load data
  useEffect(() => {
    const initializeApp = async () => {
      try {
        setIsLoading(true);

        // Initialize API service
        const apiSvc = new ApiService(config);
        setApiService(apiSvc);

        // Initialize Audio service
        const audioSvc = new AudioService();
        setAudioService(audioSvc);

        // Load API endpoints
        if (apiEndpoints && apiEndpoints.api_endpoints) {
          const formattedEndpoints: ApiEndpoint[] = [];
          
          apiEndpoints.api_endpoints.forEach(category => {
            category.endpoints.forEach(endpoint => {
              formattedEndpoints.push({
                ...endpoint,
                method: endpoint.method as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
                category: category.category
              });
            });
          });
          
          setEndpoints(formattedEndpoints);
        }

        // Check for resume data
        const resumeData = loadResumeData();
        if (resumeData) {
          // Create session from resume data
          const session: TestSession = {
            id: resumeData.sessionId,
            name: `Resumed Session - ${new Date().toLocaleString()}`,
            startTime: resumeData.timestamp,
            status: 'paused',
            totalTests: 0,
            completedTests: resumeData.lastCompletedIndex,
            successfulTests: resumeData.partialResults.filter(r => r.status === 'success').length,
            failedTests: resumeData.partialResults.filter(r => r.status === 'error').length,
            results: resumeData.partialResults,
            config: resumeData.config
          };
          
          setCurrentSession(session);
          setConfig(resumeData.config);
        }

        setIsLoading(false);
      } catch (error) {
        console.error('Failed to initialize app:', error);
        setIsLoading(false);
      }
    };

    initializeApp();
  }, []);

  // Update API service when config changes
  useEffect(() => {
    if (apiService) {
      apiService.updateConfig(config);
    }
  }, [config, apiService]);

  // Handle session updates
  const handleSessionUpdate = (session: TestSession) => {
    setCurrentSession(session);
  };

  // Handle config updates
  const handleConfigUpdate = (newConfig: TestConfig) => {
    setConfig(newConfig);
  };

  // Handle new session creation
  const handleNewSession = (name: string, selectedEndpoints: ApiEndpoint[]) => {
    const session: TestSession = {
      id: generateId(),
      name,
      startTime: new Date(),
      status: 'running',
      totalTests: selectedEndpoints.length,
      completedTests: 0,
      successfulTests: 0,
      failedTests: 0,
      results: [],
      config: { ...config }
    };

    setCurrentSession(session);
    return session;
  };

  // Handle audio recording events
  const handleAudioRecording = (recording: AudioRecording) => {
    console.log('Audio recording event:', recording);
    // Handle audio recording updates here
  };

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <Router>
      <GlobalStyle />
      <AppContainer>
        <Header 
          currentSession={currentSession}
          audioService={audioService}
          onAudioRecording={handleAudioRecording}
        />
        
        <MainContent>
          <Routes>
            <Route 
              path="/" 
              element={
                <Dashboard 
                  endpoints={endpoints}
                  currentSession={currentSession}
                  config={config}
                  onNewSession={handleNewSession}
                  onConfigUpdate={handleConfigUpdate}
                />
              } 
            />
            
            <Route 
              path="/test" 
              element={
                currentSession ? (
                  <TestRunner 
                    session={currentSession}
                    endpoints={endpoints}
                    apiService={apiService}
                    audioService={audioService}
                    onSessionUpdate={handleSessionUpdate}
                  />
                ) : (
                  <Navigate to="/" replace />
                )
              } 
            />
            
            <Route 
              path="/results" 
              element={
                <Results 
                  sessions={currentSession ? [currentSession] : []}
                  onSessionSelect={setCurrentSession}
                />
              } 
            />
            
            <Route 
              path="/audio" 
              element={
                <AudioRecorder 
                  audioService={audioService}
                  currentSession={currentSession}
                  onRecordingUpdate={handleAudioRecording}
                />
              } 
            />
            
            <Route 
              path="/settings" 
              element={
                <Settings 
                  config={config}
                  onConfigUpdate={handleConfigUpdate}
                  endpoints={endpoints}
                />
              } 
            />
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MainContent>

        <ToastContainer
          position="top-right"
          autoClose={5000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          className="toast-container"
        />
      </AppContainer>
    </Router>
  );
}

export default App;
