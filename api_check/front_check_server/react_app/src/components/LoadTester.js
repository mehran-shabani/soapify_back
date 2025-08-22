import React, { useState } from 'react';
import styled from 'styled-components';
import { toast } from 'react-toastify';
import { testRunner } from '../services/apiService';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

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

const ConfigSection = styled.div`
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
`;

const InputGroup = styled.div`
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 15px;
`;

const Label = styled.label`
  font-weight: 600;
  color: #34495e;
  min-width: 150px;
`;

const Select = styled.select`
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  flex: 1;
`;

const Input = styled.input`
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  flex: 1;
`;

const Button = styled.button`
  background-color: ${props => props.running ? '#e74c3c' : '#3498db'};
  color: white;
  border: none;
  padding: 12px 24px;
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

const ResultsSection = styled.div`
  margin-top: 30px;
`;

const StatsCard = styled.div`
  background: #ecf0f1;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
`;

const StatGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
`;

const StatItem = styled.div`
  text-align: center;
`;

const StatValue = styled.div`
  font-size: 36px;
  font-weight: bold;
  color: ${props => props.success ? '#27ae60' : props.error ? '#e74c3c' : '#3498db'};
`;

const StatLabel = styled.div`
  color: #7f8c8d;
  margin-top: 5px;
`;

const ChartContainer = styled.div`
  margin-top: 30px;
  height: 400px;
`;

function LoadTester() {
  const [config, setConfig] = useState({
    service: 'checklist',
    method: 'create',
    concurrentRequests: 10
  });
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState(null);

  const handleConfigChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const runLoadTest = async () => {
    setIsRunning(true);
    toast.info(`شروع تست بار با ${config.concurrentRequests} درخواست همزمان...`);

    try {
      const testResults = await testRunner.runLoadTest(
        config.service,
        config.method,
        config.concurrentRequests
      );
      
      setResults(testResults);
      
      if (testResults.stats.successRate === 100) {
        toast.success('تست بار با موفقیت کامل انجام شد!');
      } else if (testResults.stats.successRate > 0) {
        toast.warning(`تست بار انجام شد. نرخ موفقیت: ${testResults.stats.successRate.toFixed(1)}%`);
      } else {
        toast.error('تست بار با شکست مواجه شد');
      }
    } catch (error) {
      toast.error(`خطا در اجرای تست بار: ${error.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const getChartData = () => {
    if (!results || !results.results) return null;

    const sortedResults = [...results.results].sort((a, b) => a.index - b.index);
    
    return {
      labels: sortedResults.map(r => `Request ${r.index + 1}`),
      datasets: [
        {
          label: 'زمان پاسخ (ms)',
          data: sortedResults.map(r => r.responseTime || 0),
          borderColor: '#3498db',
          backgroundColor: 'rgba(52, 152, 219, 0.1)',
          tension: 0.1
        }
      ]
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'زمان پاسخ درخواست‌ها'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'زمان (میلی‌ثانیه)'
        }
      }
    }
  };

  return (
    <Container>
      <Title>تست بار (Load Testing)</Title>

      <ConfigSection>
        <h3>تنظیمات تست</h3>
        
        <InputGroup>
          <Label>سرویس:</Label>
          <Select 
            value={config.service} 
            onChange={(e) => handleConfigChange('service', e.target.value)}
            disabled={isRunning}
          >
            <option value="checklist">چک‌لیست</option>
            <option value="voice">آپلود صدا</option>
          </Select>
        </InputGroup>

        <InputGroup>
          <Label>عملیات:</Label>
          <Select 
            value={config.method} 
            onChange={(e) => handleConfigChange('method', e.target.value)}
            disabled={isRunning}
          >
            {config.service === 'checklist' && (
              <>
                <option value="create">ایجاد</option>
                <option value="getAll">دریافت همه</option>
              </>
            )}
            {config.service === 'voice' && (
              <>
                <option value="uploadAudio">آپلود</option>
                <option value="getRecordings">دریافت لیست</option>
              </>
            )}
          </Select>
        </InputGroup>

        <InputGroup>
          <Label>تعداد درخواست‌ها:</Label>
          <Input 
            type="number" 
            min="1" 
            max="100"
            value={config.concurrentRequests}
            onChange={(e) => handleConfigChange('concurrentRequests', parseInt(e.target.value))}
            disabled={isRunning}
          />
        </InputGroup>

        <Button onClick={runLoadTest} disabled={isRunning} running={isRunning}>
          {isRunning ? 'در حال اجرا...' : 'شروع تست بار'}
        </Button>
      </ConfigSection>

      {results && (
        <ResultsSection>
          <StatsCard>
            <h3>نتایج تست بار</h3>
            <StatGrid>
              <StatItem>
                <StatValue>{results.stats.totalRequests}</StatValue>
                <StatLabel>کل درخواست‌ها</StatLabel>
              </StatItem>
              <StatItem>
                <StatValue success>{results.stats.successfulRequests}</StatValue>
                <StatLabel>موفق</StatLabel>
              </StatItem>
              <StatItem>
                <StatValue error>{results.stats.failedRequests}</StatValue>
                <StatLabel>ناموفق</StatLabel>
              </StatItem>
              <StatItem>
                <StatValue>{results.stats.successRate.toFixed(1)}%</StatValue>
                <StatLabel>نرخ موفقیت</StatLabel>
              </StatItem>
            </StatGrid>
          </StatsCard>

          <StatsCard>
            <h3>آمار زمان پاسخ</h3>
            <StatGrid>
              <StatItem>
                <StatValue>{results.stats.responseTimes.min.toFixed(0)} ms</StatValue>
                <StatLabel>حداقل</StatLabel>
              </StatItem>
              <StatItem>
                <StatValue>{results.stats.responseTimes.avg.toFixed(0)} ms</StatValue>
                <StatLabel>میانگین</StatLabel>
              </StatItem>
              <StatItem>
                <StatValue>{results.stats.responseTimes.median.toFixed(0)} ms</StatValue>
                <StatLabel>میانه</StatLabel>
              </StatItem>
              <StatItem>
                <StatValue>{results.stats.responseTimes.max.toFixed(0)} ms</StatValue>
                <StatLabel>حداکثر</StatLabel>
              </StatItem>
            </StatGrid>
          </StatsCard>

          {getChartData() && (
            <ChartContainer>
              <Line data={getChartData()} options={chartOptions} />
            </ChartContainer>
          )}
        </ResultsSection>
      )}
    </Container>
  );
}

export default LoadTester;