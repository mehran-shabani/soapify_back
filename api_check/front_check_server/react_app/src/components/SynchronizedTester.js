import React, { useState } from 'react';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import { testRunner } from '../services/apiService';
import { serverSync, runParallelTests } from '../services/serverSync';

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

const ControlPanel = styled.div`
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  text-align: center;
`;

const Button = styled.button`
  background-color: ${props => 
    props.variant === 'sync' ? '#9b59b6' : 
    props.variant === 'parallel' ? '#e67e22' : '#3498db'};
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

const ResultsContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 20px;
`;

const ResultCard = styled.div`
  background: #ecf0f1;
  padding: 20px;
  border-radius: 8px;
  border-top: 4px solid ${props => props.source === 'frontend' ? '#3498db' : '#e74c3c'};
`;

const ResultTitle = styled.h3`
  margin-bottom: 15px;
  color: #34495e;
`;

const ComparisonCard = styled.div`
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
  border: 2px solid ${props => props.hasDiscrepancies ? '#e74c3c' : '#27ae60'};
`;

const MetricRow = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #ddd;

  &:last-child {
    border-bottom: none;
  }
`;

const MetricLabel = styled.span`
  font-weight: 600;
  color: #34495e;
`;

const MetricValue = styled.span`
  color: ${props => props.success ? '#27ae60' : props.error ? '#e74c3c' : '#3498db'};
`;

const StatusIndicator = styled.div`
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 10px;
  background-color: ${props => 
    props.status === 'running' ? '#f39c12' :
    props.status === 'completed' ? '#27ae60' :
    props.status === 'failed' ? '#e74c3c' : '#95a5a6'
  };
  animation: ${props => props.status === 'running' ? 'pulse 1s infinite' : 'none'};

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const ServerStatus = styled.div`
  position: absolute;
  top: 20px;
  left: 20px;
  background: white;
  padding: 10px 20px;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
`;

function SynchronizedTester() {
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [serverStatus, setServerStatus] = useState('idle');
  const [testMode, setTestMode] = useState('sync'); // 'sync' or 'parallel'

  const runSynchronizedTest = async () => {
    setIsRunning(true);
    setServerStatus('running');
    toast.info('شروع تست همزمان...');

    try {
      const syncResults = await serverSync.runSynchronizedTests(
        testRunner.runAllTests
      );
      
      setResults(syncResults);
      
      // Check for discrepancies
      const hasDiscrepancies = syncResults.comparison.discrepancies.length > 0;
      
      if (hasDiscrepancies) {
        toast.warning(`تست کامل شد اما ${syncResults.comparison.discrepancies.length} ناهماهنگی یافت شد`);
      } else {
        toast.success('تست همزمان با موفقیت و بدون ناهماهنگی انجام شد!');
      }
      
      setServerStatus('completed');
    } catch (error) {
      toast.error(`خطا در تست همزمان: ${error.message}`);
      setServerStatus('failed');
    } finally {
      setIsRunning(false);
    }
  };

  const runParallelTest = async () => {
    setIsRunning(true);
    setServerStatus('running');
    toast.info('شروع تست موازی...');

    try {
      const parallelResults = await runParallelTests(
        testRunner.runAllTests,
        'all'
      );
      
      setResults({
        ...parallelResults,
        comparison: compareParallelResults(parallelResults)
      });
      
      toast.success(`تست موازی در ${parallelResults.totalTime}ms انجام شد`);
      setServerStatus('completed');
    } catch (error) {
      toast.error(`خطا در تست موازی: ${error.message}`);
      setServerStatus('failed');
    } finally {
      setIsRunning(false);
    }
  };

  const compareParallelResults = (results) => {
    // Simple comparison for parallel results
    const comparison = {
      response_time_diff: {},
      success_match: {},
      discrepancies: []
    };

    if (results.frontend && results.server) {
      // Compare each test type
      ['voice', 'stt', 'checklist'].forEach(testType => {
        if (results.frontend[testType] && results.server[testType]) {
          const frontSuccess = results.frontend[testType].success;
          const serverSuccess = results.server[testType].success;
          
          comparison.success_match[testType] = frontSuccess === serverSuccess;
          
          if (!comparison.success_match[testType]) {
            comparison.discrepancies.push({
              test: testType,
              issue: 'Success status mismatch in parallel execution'
            });
          }
        }
      });
    }

    return comparison;
  };

  const renderTestResult = (result, source) => {
    if (!result) return <div>No results</div>;

    return (
      <ResultCard source={source}>
        <ResultTitle>
          {source === 'frontend' ? '🖥️ نتایج Frontend' : '🖥️ نتایج Server'}
        </ResultTitle>
        
        {['voice', 'stt', 'checklist'].map(testType => (
          result[testType] && (
            <div key={testType} style={{ marginBottom: '15px' }}>
              <h4>{testType.toUpperCase()} Test</h4>
              <MetricRow>
                <MetricLabel>وضعیت:</MetricLabel>
                <MetricValue success={result[testType].success}>
                  {result[testType].success ? '✅ موفق' : '❌ ناموفق'}
                </MetricValue>
              </MetricRow>
              <MetricRow>
                <MetricLabel>زمان پاسخ:</MetricLabel>
                <MetricValue>
                  {result[testType].responseTime || result[testType].response_time_ms} ms
                </MetricValue>
              </MetricRow>
            </div>
          )
        ))}
      </ResultCard>
    );
  };

  const renderComparison = (comparison) => {
    if (!comparison) return null;

    const hasDiscrepancies = comparison.discrepancies.length > 0;

    return (
      <ComparisonCard hasDiscrepancies={hasDiscrepancies}>
        <h3>📊 مقایسه نتایج</h3>
        
        {hasDiscrepancies ? (
          <>
            <p style={{ color: '#e74c3c' }}>
              ⚠️ {comparison.discrepancies.length} ناهماهنگی یافت شد:
            </p>
            {comparison.discrepancies.map((disc, index) => (
              <div key={index} style={{ 
                background: '#fff', 
                padding: '10px', 
                marginBottom: '5px',
                borderRadius: '4px'
              }}>
                <strong>{disc.test}:</strong> {disc.issue}
              </div>
            ))}
          </>
        ) : (
          <p style={{ color: '#27ae60' }}>
            ✅ همه تست‌ها در Frontend و Server نتایج یکسانی داشتند
          </p>
        )}

        {comparison.response_time_diff && (
          <div style={{ marginTop: '20px' }}>
            <h4>تفاوت زمان پاسخ:</h4>
            {Object.entries(comparison.response_time_diff).map(([test, diff]) => (
              <MetricRow key={test}>
                <MetricLabel>{test}:</MetricLabel>
                <MetricValue>
                  Frontend: {diff.frontend_ms}ms | Server: {diff.server_ms}ms | 
                  تفاوت: {diff.difference_ms}ms
                </MetricValue>
              </MetricRow>
            ))}
          </div>
        )}
      </ComparisonCard>
    );
  };

  return (
    <Container style={{ position: 'relative' }}>
      <ServerStatus>
        <StatusIndicator status={serverStatus} />
        <span>وضعیت سرور: {
          serverStatus === 'idle' ? 'آماده' :
          serverStatus === 'running' ? 'در حال اجرا' :
          serverStatus === 'completed' ? 'تکمیل شده' :
          'خطا'
        }</span>
      </ServerStatus>

      <Title>تست همزمان Frontend و Server</Title>

      <ControlPanel>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ marginRight: '20px' }}>
            <input
              type="radio"
              value="sync"
              checked={testMode === 'sync'}
              onChange={(e) => setTestMode(e.target.value)}
              style={{ marginLeft: '5px' }}
            />
            تست همزمان (Synchronized)
          </label>
          <label>
            <input
              type="radio"
              value="parallel"
              checked={testMode === 'parallel'}
              onChange={(e) => setTestMode(e.target.value)}
              style={{ marginLeft: '5px' }}
            />
            تست موازی (Parallel)
          </label>
        </div>

        <Button
          variant={testMode}
          onClick={testMode === 'sync' ? runSynchronizedTest : runParallelTest}
          disabled={isRunning}
        >
          {isRunning ? 'در حال اجرا...' : 
           testMode === 'sync' ? 'اجرای تست همزمان' : 'اجرای تست موازی'}
        </Button>

        <p style={{ marginTop: '10px', color: '#7f8c8d', fontSize: '14px' }}>
          {testMode === 'sync' 
            ? 'تست‌ها ابتدا در Frontend اجرا شده و سپس نتایج به Server ارسال می‌شود'
            : 'تست‌ها به صورت موازی در Frontend و Server اجرا می‌شوند'}
        </p>
      </ControlPanel>

      {results && (
        <>
          <ResultsContainer>
            {results.frontend && renderTestResult(
              results.frontend.results || results.frontend, 
              'frontend'
            )}
            {results.server && renderTestResult(
              results.server.results || results.server, 
              'server'
            )}
          </ResultsContainer>

          {results.comparison && renderComparison(results.comparison)}

          {results.totalTime && (
            <div style={{ textAlign: 'center', marginTop: '20px', color: '#7f8c8d' }}>
              زمان کل اجرا: {results.totalTime}ms
            </div>
          )}
        </>
      )}
    </Container>
  );
}

export default SynchronizedTester;