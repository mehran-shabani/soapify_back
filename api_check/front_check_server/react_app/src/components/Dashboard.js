import React from 'react';
import styled from 'styled-components';
import { Pie, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
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

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
`;

const StatCard = styled.div`
  background: ${props => props.color || '#ecf0f1'};
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  transition: transform 0.3s;

  &:hover {
    transform: translateY(-5px);
  }
`;

const StatValue = styled.div`
  font-size: 48px;
  font-weight: bold;
  color: white;
  margin-bottom: 10px;
`;

const StatLabel = styled.div`
  color: rgba(255, 255, 255, 0.9);
  font-size: 16px;
`;

const ChartsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 30px;
  margin-top: 30px;
`;

const ChartContainer = styled.div`
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  height: 400px;
`;

const ChartTitle = styled.h3`
  margin-bottom: 20px;
  color: #34495e;
  text-align: center;
`;

const InfoSection = styled.div`
  background: #ecf0f1;
  padding: 20px;
  border-radius: 8px;
  margin-top: 30px;
`;

const InfoGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
`;

const InfoItem = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 10px;
  background: white;
  border-radius: 4px;
`;

const InfoLabel = styled.span`
  color: #7f8c8d;
`;

const InfoValue = styled.span`
  color: #2c3e50;
  font-weight: 600;
`;

function Dashboard({ data, results }) {
  // Calculate API-specific stats
  const getApiStats = () => {
    if (!results || results.length === 0) {
      return { voice: 0, stt: 0, checklist: 0 };
    }

    const stats = {
      voice: { success: 0, failed: 0, total: 0, avgTime: 0 },
      stt: { success: 0, failed: 0, total: 0, avgTime: 0 },
      checklist: { success: 0, failed: 0, total: 0, avgTime: 0 }
    };

    const times = { voice: [], stt: [], checklist: [] };

    results.forEach(result => {
      // Voice stats
      if (result.voice) {
        stats.voice.total++;
        if (result.voice.success) {
          stats.voice.success++;
          times.voice.push(result.voice.responseTime);
        } else {
          stats.voice.failed++;
        }
      }

      // STT stats
      if (result.stt) {
        stats.stt.total++;
        if (result.stt.success) {
          stats.stt.success++;
          times.stt.push(result.stt.responseTime);
        } else {
          stats.stt.failed++;
        }
      }

      // Checklist stats
      if (result.checklist) {
        stats.checklist.total++;
        if (result.checklist.success) {
          stats.checklist.success++;
          times.checklist.push(result.checklist.responseTime);
        } else {
          stats.checklist.failed++;
        }
      }
    });

    // Calculate average times
    Object.keys(times).forEach(key => {
      if (times[key].length > 0) {
        stats[key].avgTime = times[key].reduce((a, b) => a + b, 0) / times[key].length;
      }
    });

    return stats;
  };

  const apiStats = getApiStats();

  // Pie chart data for success/failure ratio
  const pieChartData = {
    labels: ['موفق', 'ناموفق'],
    datasets: [
      {
        label: 'نسبت موفقیت',
        data: [
          apiStats.voice.success + apiStats.stt.success + apiStats.checklist.success,
          apiStats.voice.failed + apiStats.stt.failed + apiStats.checklist.failed
        ],
        backgroundColor: ['#27ae60', '#e74c3c'],
        borderColor: ['#229954', '#c0392b'],
        borderWidth: 1,
      },
    ],
  };

  // Bar chart data for response times
  const barChartData = {
    labels: ['آپلود صدا', 'تبدیل گفتار به متن', 'چک‌لیست'],
    datasets: [
      {
        label: 'میانگین زمان پاسخ (ms)',
        data: [
          apiStats.voice.avgTime,
          apiStats.stt.avgTime,
          apiStats.checklist.avgTime
        ],
        backgroundColor: ['#3498db', '#9b59b6', '#f39c12'],
        borderColor: ['#2980b9', '#8e44ad', '#e67e22'],
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'نامشخص';
    try {
      return new Date(dateString).toLocaleString('fa-IR');
    } catch {
      return dateString;
    }
  };

  return (
    <Container>
      <Title>داشبورد آماری</Title>

      <StatsGrid>
        <StatCard color="#3498db">
          <StatValue>{data.totalTests}</StatValue>
          <StatLabel>کل تست‌ها</StatLabel>
        </StatCard>
        <StatCard color="#27ae60">
          <StatValue>{data.successRate.toFixed(0)}%</StatValue>
          <StatLabel>نرخ موفقیت</StatLabel>
        </StatCard>
        <StatCard color="#f39c12">
          <StatValue>{data.avgResponseTime} ms</StatValue>
          <StatLabel>میانگین زمان پاسخ</StatLabel>
        </StatCard>
      </StatsGrid>

      <ChartsGrid>
        <ChartContainer>
          <ChartTitle>نسبت موفقیت به شکست</ChartTitle>
          <Pie data={pieChartData} options={chartOptions} />
        </ChartContainer>

        <ChartContainer>
          <ChartTitle>میانگین زمان پاسخ API ها</ChartTitle>
          <Bar data={barChartData} options={chartOptions} />
        </ChartContainer>
      </ChartsGrid>

      <InfoSection>
        <h3>جزئیات آماری</h3>
        <InfoGrid>
          <InfoItem>
            <InfoLabel>آخرین بروزرسانی:</InfoLabel>
            <InfoValue>{formatDate(data.lastUpdated)}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>تست‌های آپلود صدا:</InfoLabel>
            <InfoValue>{apiStats.voice.total}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>تست‌های تبدیل گفتار:</InfoLabel>
            <InfoValue>{apiStats.stt.total}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>تست‌های چک‌لیست:</InfoLabel>
            <InfoValue>{apiStats.checklist.total}</InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>نرخ موفقیت آپلود:</InfoLabel>
            <InfoValue>
              {apiStats.voice.total > 0 
                ? `${((apiStats.voice.success / apiStats.voice.total) * 100).toFixed(1)}%`
                : 'N/A'}
            </InfoValue>
          </InfoItem>
          <InfoItem>
            <InfoLabel>نرخ موفقیت STT:</InfoLabel>
            <InfoValue>
              {apiStats.stt.total > 0 
                ? `${((apiStats.stt.success / apiStats.stt.total) * 100).toFixed(1)}%`
                : 'N/A'}
            </InfoValue>
          </InfoItem>
        </InfoGrid>
      </InfoSection>
    </Container>
  );
}

export default Dashboard;