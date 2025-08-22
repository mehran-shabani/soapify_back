import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import axios from 'axios';

const Container = styled.div`
  padding: 20px;
  background: #1a1a1a;
  border-radius: 10px;
  color: white;
`;

const Title = styled.h2`
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const ErrorDisplay = styled.div`
  background: #2a2a2a;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #ff4444;
`;

const DiagnosisSection = styled.div`
  margin-bottom: 30px;
`;

const IssueCard = styled.div`
  background: #2a2a2a;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 4px solid ${props => {
    switch(props.level) {
      case 'green': return '#4CAF50';
      case 'yellow': return '#FFC107';
      case 'red': return '#f44336';
      default: return '#666';
    }
  }};
`;

const SolutionCard = styled.div`
  background: #2a2a2a;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
`;

const CommandBlock = styled.div`
  background: #1a1a1a;
  padding: 15px;
  border-radius: 5px;
  margin: 10px 0;
  position: relative;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  overflow-x: auto;
`;

const CopyButton = styled.button`
  position: absolute;
  top: 5px;
  right: 5px;
  background: #4CAF50;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  
  &:hover {
    background: #45a049;
  }
`;

const CommandLabel = styled.div`
  color: #888;
  font-size: 12px;
  margin-bottom: 5px;
`;

const LevelIndicator = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 15px;
  font-size: 12px;
  background: ${props => {
    switch(props.level) {
      case 'green': return '#4CAF5033';
      case 'yellow': return '#FFC10733';
      case 'red': return '#f4433633';
      default: return '#66666633';
    }
  }};
  color: ${props => {
    switch(props.level) {
      case 'green': return '#4CAF50';
      case 'yellow': return '#FFC107';
      case 'red': return '#f44336';
      default: return '#666';
    }
  }};
`;

const TestSequenceStep = styled.div`
  background: #2a2a2a;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const StepNumber = styled.div`
  width: 30px;
  height: 30px;
  background: #4CAF50;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 15px;
`;

const QuickFixButton = styled.button`
  background: #FF9800;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  margin-right: 10px;
  
  &:hover {
    background: #F57C00;
  }
`;

const TabContainer = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
`;

const Tab = styled.button`
  padding: 10px 20px;
  background: ${props => props.active ? '#4CAF50' : '#2a2a2a'};
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  
  &:hover {
    background: ${props => props.active ? '#4CAF50' : '#3a3a3a'};
  }
`;

const OptimizationPanel = styled.div`
  background: #2a2a2a;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 20px;
  background: #1a1a1a;
  border-radius: 10px;
  overflow: hidden;
  margin: 10px 0;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: #4CAF50;
  width: ${props => props.progress}%;
  transition: width 0.3s ease;
`;

const SERVER_URL = process.env.REACT_APP_SERVER_MONITOR_URL || 'http://localhost:8001';

const DiagnosticPanel = ({ lastError, currentEndpoint }) => {
  const [activeTab, setActiveTab] = useState('diagnosis');
  const [diagnosis, setDiagnosis] = useState(null);
  const [testSequence, setTestSequence] = useState(null);
  const [optimizationStatus, setOptimizationStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lastError) {
      analyzeDiagnostics(lastError);
    }
  }, [lastError]);

  const analyzeDiagnostics = async (error) => {
    setLoading(true);
    try {
      const response = await axios.post(`${SERVER_URL}/api/diagnostics/analyze`, {
        error_message: error.message || error.toString(),
        context: {
          endpoint: currentEndpoint,
          host: 'django-m.chbk.app',
          timestamp: new Date().toISOString()
        }
      });
      setDiagnosis(response.data);
    } catch (err) {
      console.error('Diagnostic analysis failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const getTestSequence = async () => {
    if (!currentEndpoint) return;
    
    try {
      const response = await axios.get(`${SERVER_URL}/api/diagnostics/test-sequence/${currentEndpoint}`);
      setTestSequence(response.data.sequence);
    } catch (err) {
      console.error('Failed to get test sequence:', err);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success('کپی شد! 📋');
    });
  };

  const runOptimization = async () => {
    setOptimizationStatus({ running: true, progress: 0 });
    try {
      const response = await axios.post(`${SERVER_URL}/api/optimizer/test-approaches`);
      setOptimizationStatus({ 
        running: false, 
        results: response.data,
        progress: 100 
      });
      toast.success('بهینه‌سازی با موفقیت انجام شد! 🚀');
    } catch (err) {
      console.error('Optimization failed:', err);
      setOptimizationStatus({ running: false, error: err.message });
      toast.error('بهینه‌سازی شکست خورد');
    }
  };

  const applyOptimizations = async () => {
    if (!optimizationStatus?.results?.best_configurations) return;
    
    try {
      const response = await axios.post(`${SERVER_URL}/api/optimizer/apply`, {
        best_configs: optimizationStatus.results.best_configurations
      });
      
      if (response.data.success) {
        toast.success('بهینه‌سازی‌ها اعمال شد! فایل ZIP آماده دانلود است 📦');
        // Trigger download
        window.open(`${SERVER_URL}/${response.data.zip_path}`, '_blank');
      }
    } catch (err) {
      console.error('Failed to apply optimizations:', err);
      toast.error('اعمال بهینه‌سازی شکست خورد');
    }
  };

  const runCommand = async (command, level) => {
    if (level === 'desktop') {
      copyToClipboard(command);
      toast.info('دستور کپی شد! آن را در ترمینال خود اجرا کنید');
    } else {
      copyToClipboard(command);
      toast.warning('این دستور باید روی سرور اجرا شود. دستور کپی شد.');
    }
  };

  const getLevelIcon = (level) => {
    switch(level) {
      case 'green': return '🟢';
      case 'yellow': return '🟡';
      case 'red': return '🔴';
      default: return '⚪';
    }
  };

  const getLevelText = (level) => {
    switch(level) {
      case 'green': return 'قابل حل توسط شما';
      case 'yellow': return 'نیاز به همکاری';
      case 'red': return 'فقط Admin سرور';
      default: return 'نامشخص';
    }
  };

  if (!lastError && !currentEndpoint) {
    return (
      <Container>
        <Title>🔧 پنل تشخیص خطا</Title>
        <p style={{ color: '#888' }}>هنوز خطایی رخ نداده است. وقتی خطایی رخ دهد، اینجا راه‌حل‌ها را خواهید دید.</p>
      </Container>
    );
  }

  return (
    <Container>
      <Title>
        🔧 پنل تشخیص خطا
        {loading && <span style={{ fontSize: '16px', color: '#888' }}>در حال تحلیل...</span>}
      </Title>

      <TabContainer>
        <Tab active={activeTab === 'diagnosis'} onClick={() => setActiveTab('diagnosis')}>
          تشخیص خطا
        </Tab>
        <Tab active={activeTab === 'sequence'} onClick={() => { setActiveTab('sequence'); getTestSequence(); }}>
          دنباله تست
        </Tab>
        <Tab active={activeTab === 'optimization'} onClick={() => setActiveTab('optimization')}>
          بهینه‌سازی
        </Tab>
      </TabContainer>

      {activeTab === 'diagnosis' && diagnosis && (
        <>
          {lastError && (
            <ErrorDisplay>
              <h4>خطای رخ داده:</h4>
              <pre style={{ margin: '10px 0', whiteSpace: 'pre-wrap' }}>
                {lastError.message || lastError.toString()}
              </pre>
              <small style={{ color: '#888' }}>
                زمان: {new Date().toLocaleTimeString('fa-IR')}
              </small>
            </ErrorDisplay>
          )}

          <DiagnosisSection>
            <h3>مشکلات تشخیص داده شده:</h3>
            {diagnosis.detected_issues.map((issue, index) => (
              <IssueCard key={index} level={issue.level}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <strong>{getLevelIcon(issue.level)} {issue.type.toUpperCase()}</strong>
                  <LevelIndicator level={issue.level}>
                    {getLevelText(issue.level)}
                  </LevelIndicator>
                </div>
                <p>دسته: {issue.category}</p>
                <p>اطمینان: {(issue.confidence * 100).toFixed(0)}%</p>
              </IssueCard>
            ))}
          </DiagnosisSection>

          {diagnosis.solutions && diagnosis.solutions.length > 0 && (
            <DiagnosisSection>
              <h3>راه‌حل‌های پیشنهادی:</h3>
              {diagnosis.solutions.map((solution, sIndex) => (
                <SolutionCard key={sIndex}>
                  <h4>{solution.issue_type}</h4>
                  <p style={{ marginBottom: '15px' }}>{solution.explanation}</p>
                  
                  {solution.commands.desktop && solution.commands.desktop.length > 0 && (
                    <div>
                      <h5 style={{ color: '#4CAF50' }}>
                        🖥️ دستورات Desktop (شما اجرا کنید):
                      </h5>
                      {solution.commands.desktop.map((cmd, cIndex) => (
                        <CommandBlock key={cIndex}>
                          <CommandLabel>{cmd.description}</CommandLabel>
                          <pre style={{ margin: 0 }}>{cmd.command}</pre>
                          <CopyButton onClick={() => copyToClipboard(cmd.command)}>
                            کپی
                          </CopyButton>
                        </CommandBlock>
                      ))}
                    </div>
                  )}
                  
                  {solution.commands.server && solution.commands.server.length > 0 && (
                    <div style={{ marginTop: '20px' }}>
                      <h5 style={{ color: '#ff9800' }}>
                        🖥️ دستورات Server (به Admin بگویید):
                      </h5>
                      {solution.commands.server.map((cmd, cIndex) => (
                        <CommandBlock key={cIndex}>
                          <CommandLabel>{cmd.description}</CommandLabel>
                          <pre style={{ margin: 0 }}>{cmd.command}</pre>
                          <CopyButton onClick={() => copyToClipboard(cmd.command)}>
                            کپی
                          </CopyButton>
                        </CommandBlock>
                      ))}
                    </div>
                  )}

                  <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
                    {solution.can_user_fix && (
                      <QuickFixButton onClick={() => runCommand(solution.commands.desktop[0]?.command, 'desktop')}>
                        اجرای سریع
                      </QuickFixButton>
                    )}
                    {solution.needs_cooperation && (
                      <QuickFixButton style={{ background: '#FFC107' }}>
                        نیاز به همکاری Admin
                      </QuickFixButton>
                    )}
                    {solution.admin_only && (
                      <QuickFixButton style={{ background: '#f44336' }} disabled>
                        فقط Admin
                      </QuickFixButton>
                    )}
                  </div>
                </SolutionCard>
              ))}
            </DiagnosisSection>
          )}
        </>
      )}

      {activeTab === 'sequence' && testSequence && (
        <DiagnosisSection>
          <h3>دنباله تست برای {currentEndpoint}:</h3>
          {testSequence.map((step, index) => (
            <TestSequenceStep key={index}>
              <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                <StepNumber>{step.step}</StepNumber>
                <div style={{ flex: 1 }}>
                  <h5>{step.description}</h5>
                  <CommandBlock style={{ margin: '10px 0' }}>
                    <pre style={{ margin: 0 }}>{step.command}</pre>
                    <CopyButton onClick={() => copyToClipboard(step.command)}>
                      کپی
                    </CopyButton>
                  </CommandBlock>
                  <small style={{ color: '#888' }}>
                    انتظار: {step.expected} | در صورت خطا: {step.on_failure}
                  </small>
                </div>
              </div>
              <LevelIndicator level={step.level === 'desktop' ? 'green' : 'yellow'}>
                {step.level === 'desktop' ? 'Local' : 'Server'}
              </LevelIndicator>
            </TestSequenceStep>
          ))}
        </DiagnosisSection>
      )}

      {activeTab === 'optimization' && (
        <OptimizationPanel>
          <h3>🚀 بهینه‌سازی API</h3>
          <p style={{ marginBottom: '20px' }}>
            سیستم روش‌های مختلف پیاده‌سازی API را تست می‌کند و بهترین پیکربندی را انتخاب می‌کند.
          </p>
          
          {!optimizationStatus && (
            <QuickFixButton onClick={runOptimization}>
              شروع بهینه‌سازی
            </QuickFixButton>
          )}
          
          {optimizationStatus?.running && (
            <div>
              <p>در حال تست روش‌های مختلف...</p>
              <ProgressBar>
                <ProgressFill progress={optimizationStatus.progress} />
              </ProgressBar>
            </div>
          )}
          
          {optimizationStatus?.results && (
            <div>
              <h4>نتایج بهینه‌سازی:</h4>
              {Object.entries(optimizationStatus.results.test_results).map(([category, results]) => (
                <div key={category} style={{ marginBottom: '20px' }}>
                  <h5>{category.toUpperCase()}</h5>
                  <div style={{ background: '#1a1a1a', padding: '10px', borderRadius: '5px' }}>
                    <p>بهترین روش: <strong>{optimizationStatus.results.best_configurations[category]}</strong></p>
                    <p>بهبود عملکرد: +{((results[optimizationStatus.results.best_configurations[category]]?.optimization_score || 0) * 10).toFixed(0)}%</p>
                  </div>
                </div>
              ))}
              
              <QuickFixButton onClick={applyOptimizations} style={{ marginTop: '20px' }}>
                اعمال بهینه‌سازی‌ها و دانلود پروژه بهینه شده
              </QuickFixButton>
            </div>
          )}
        </OptimizationPanel>
      )}
    </Container>
  );
};

export default DiagnosticPanel;