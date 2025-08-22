import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import VoiceRecorder from './components/VoiceRecorder';
import TestResults from './components/TestResults';
import LoadTester from './components/LoadTester';
import Dashboard from './components/Dashboard';
import { testRunner } from './services/apiService';

const AppContainer = styled.div`
  min-height: 100vh;
  background-color: #f5f5f5;
  direction: rtl;
`;

const Header = styled.header`
  background-color: #2c3e50;
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const Title = styled.h1`
  margin: 0;
  font-size: 2rem;
`;

const Subtitle = styled.p`
  margin: 10px 0 0;
  opacity: 0.9;
`;

const MainContent = styled.main`
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
`;

const ControlPanel = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
`;

const Button = styled.button`
  background-color: ${props => props.variant === 'success' ? '#27ae60' : 
                     props.variant === 'danger' ? '#e74c3c' : '#3498db'};
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

const TabContainer = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 2px solid #ecf0f1;
`;

const Tab = styled.button`
  background: none;
  border: none;
  padding: 10px 20px;
  font-size: 16px;
  cursor: pointer;
  color: ${props => props.active ? '#3498db' : '#7f8c8d'};
  border-bottom: 3px solid ${props => props.active ? '#3498db' : 'transparent'};
  transition: all 0.3s;

  &:hover {
    color: #3498db;
  }
`;

function App() {
  const [activeTab, setActiveTab] = useState('tests');
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [testResults, setTestResults] = useState([]);
  const [dashboardData, setDashboardData] = useState({
    totalTests: 0,
    successRate: 0,
    avgResponseTime: 0,
    lastUpdated: null
  });

  useEffect(() => {
    // Load saved results from localStorage
    const savedResults = localStorage.getItem('testResults');
    if (savedResults) {
      setTestResults(JSON.parse(savedResults));
    }
  }, []);

  useEffect(() => {
    // Update dashboard data when results change
    if (testResults.length > 0) {
      const successCount = testResults.filter(r => 
        r.voice?.success && r.stt?.success && r.checklist?.success
      ).length;
      
      const allResponseTimes = testResults.flatMap(r => [
        r.voice?.responseTime || 0,
        r.stt?.responseTime || 0,
        r.checklist?.responseTime || 0
      ]).filter(t => t > 0);

      const avgResponseTime = allResponseTimes.length > 0 
        ? allResponseTimes.reduce((a, b) => a + b, 0) / allResponseTimes.length 
        : 0;

      setDashboardData({
        totalTests: testResults.length,
        successRate: (successCount / testResults.length) * 100,
        avgResponseTime: Math.round(avgResponseTime),
        lastUpdated: new Date().toISOString()
      });
    }
  }, [testResults]);

  const handleRunAllTests = async () => {
    setIsRunningTests(true);
    toast.info('شروع اجرای تست‌ها...');

    try {
      const results = await testRunner.runAllTests();
      const newResults = [...testResults, results];
      setTestResults(newResults);
      localStorage.setItem('testResults', JSON.stringify(newResults));
      
      // Check if all tests passed
      if (results.voice?.success && results.stt?.success && results.checklist?.success) {
        toast.success('همه تست‌ها با موفقیت انجام شد!');
      } else {
        toast.warning('برخی تست‌ها با خطا مواجه شدند');
      }
    } catch (error) {
      toast.error(`خطا در اجرای تست‌ها: ${error.message}`);
    } finally {
      setIsRunningTests(false);
    }
  };

  const handleClearResults = () => {
    setTestResults([]);
    localStorage.removeItem('testResults');
    toast.info('نتایج پاک شد');
  };

  const handleExportResults = () => {
    const dataStr = JSON.stringify(testResults, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `test-results-${new Date().toISOString()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    toast.success('نتایج با موفقیت دانلود شد');
  };

  return (
    <AppContainer>
      <Header>
        <Title>تست‌کننده API Soapify</Title>
        <Subtitle>تست جامع API از سمت کلاینت</Subtitle>
      </Header>

      <MainContent>
        <ControlPanel>
          <Button 
            variant="success" 
            onClick={handleRunAllTests}
            disabled={isRunningTests}
          >
            {isRunningTests ? 'در حال اجرا...' : 'اجرای همه تست‌ها'}
          </Button>
          <Button onClick={handleExportResults} disabled={testResults.length === 0}>
            دانلود نتایج
          </Button>
          <Button 
            variant="danger" 
            onClick={handleClearResults}
            disabled={testResults.length === 0}
          >
            پاک کردن نتایج
          </Button>
        </ControlPanel>

        <TabContainer>
          <Tab active={activeTab === 'tests'} onClick={() => setActiveTab('tests')}>
            تست‌های API
          </Tab>
          <Tab active={activeTab === 'voice'} onClick={() => setActiveTab('voice')}>
            ضبط صدا
          </Tab>
          <Tab active={activeTab === 'load'} onClick={() => setActiveTab('load')}>
            تست بار
          </Tab>
          <Tab active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')}>
            داشبورد
          </Tab>
        </TabContainer>

        {activeTab === 'tests' && (
          <TestResults results={testResults} />
        )}

        {activeTab === 'voice' && (
          <VoiceRecorder />
        )}

        {activeTab === 'load' && (
          <LoadTester />
        )}

        {activeTab === 'dashboard' && (
          <Dashboard data={dashboardData} results={testResults} />
        )}
      </MainContent>

      <ToastContainer 
        position="bottom-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl
        pauseOnFocusLoss
        draggable
        pauseOnHover
      />
    </AppContainer>
  );
}

export default App;