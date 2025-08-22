import React from 'react';
import styled from 'styled-components';
import { format } from 'date-fns';

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

const ResultCard = styled.div`
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  border-right: 4px solid ${props => 
    props.success ? '#27ae60' : 
    props.partial ? '#f39c12' : '#e74c3c'
  };
`;

const ResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
`;

const Timestamp = styled.span`
  color: #7f8c8d;
  font-size: 14px;
`;

const TestSection = styled.div`
  margin: 10px 0;
  padding: 10px;
  background: white;
  border-radius: 4px;
`;

const TestTitle = styled.h4`
  margin: 0 0 10px 0;
  color: #34495e;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const StatusIcon = styled.span`
  font-size: 18px;
`;

const MetricRow = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 14px;
`;

const MetricLabel = styled.span`
  color: #7f8c8d;
`;

const MetricValue = styled.span`
  color: #2c3e50;
  font-weight: 500;
`;

const NoResults = styled.div`
  text-align: center;
  padding: 40px;
  color: #7f8c8d;
`;

const ErrorMessage = styled.div`
  color: #e74c3c;
  font-size: 14px;
  margin-top: 5px;
`;

function TestResults({ results }) {
  if (!results || results.length === 0) {
    return (
      <Container>
        <Title>نتایج تست‌ها</Title>
        <NoResults>
          هنوز تستی اجرا نشده است. روی دکمه "اجرای همه تست‌ها" کلیک کنید.
        </NoResults>
      </Container>
    );
  }

  const getOverallStatus = (result) => {
    const allSuccess = result.voice?.success && result.stt?.success && result.checklist?.success;
    const someSuccess = result.voice?.success || result.stt?.success || result.checklist?.success;
    
    return {
      success: allSuccess,
      partial: !allSuccess && someSuccess,
      failed: !someSuccess
    };
  };

  const formatTimestamp = (timestamp) => {
    try {
      return format(new Date(timestamp), 'HH:mm:ss - yyyy/MM/dd');
    } catch {
      return timestamp;
    }
  };

  return (
    <Container>
      <Title>نتایج تست‌ها ({results.length} تست)</Title>
      
      {results.map((result, index) => {
        const status = getOverallStatus(result);
        
        return (
          <ResultCard key={index} {...status}>
            <ResultHeader>
              <div>
                <strong>تست #{results.length - index}</strong>
                {status.success && ' - همه تست‌ها موفق'}
                {status.partial && ' - برخی تست‌ها موفق'}
                {status.failed && ' - همه تست‌ها ناموفق'}
              </div>
              <Timestamp>{formatTimestamp(result.timestamp)}</Timestamp>
            </ResultHeader>

            {/* Voice Upload Test */}
            <TestSection>
              <TestTitle>
                <StatusIcon>{result.voice?.success ? '✅' : '❌'}</StatusIcon>
                تست آپلود صدا
              </TestTitle>
              {result.voice && (
                <>
                  <MetricRow>
                    <MetricLabel>زمان پاسخ:</MetricLabel>
                    <MetricValue>{result.voice.responseTime} ms</MetricValue>
                  </MetricRow>
                  {result.voice.fileSize && (
                    <MetricRow>
                      <MetricLabel>حجم فایل:</MetricLabel>
                      <MetricValue>{(result.voice.fileSize / 1024).toFixed(2)} KB</MetricValue>
                    </MetricRow>
                  )}
                  {result.voice.status && (
                    <MetricRow>
                      <MetricLabel>کد وضعیت:</MetricLabel>
                      <MetricValue>{result.voice.status}</MetricValue>
                    </MetricRow>
                  )}
                  {result.voice.error && (
                    <ErrorMessage>خطا: {result.voice.error}</ErrorMessage>
                  )}
                </>
              )}
            </TestSection>

            {/* STT Test */}
            <TestSection>
              <TestTitle>
                <StatusIcon>{result.stt?.success ? '✅' : '❌'}</StatusIcon>
                تست تبدیل گفتار به متن
              </TestTitle>
              {result.stt && (
                <>
                  <MetricRow>
                    <MetricLabel>زمان پاسخ:</MetricLabel>
                    <MetricValue>{result.stt.responseTime} ms</MetricValue>
                  </MetricRow>
                  {result.stt.status && (
                    <MetricRow>
                      <MetricLabel>کد وضعیت:</MetricLabel>
                      <MetricValue>{result.stt.status}</MetricValue>
                    </MetricRow>
                  )}
                  {result.stt.data?.transcription && (
                    <MetricRow>
                      <MetricLabel>متن تشخیص داده شده:</MetricLabel>
                      <MetricValue>{result.stt.data.transcription}</MetricValue>
                    </MetricRow>
                  )}
                  {result.stt.error && (
                    <ErrorMessage>خطا: {result.stt.error}</ErrorMessage>
                  )}
                </>
              )}
            </TestSection>

            {/* Checklist Test */}
            <TestSection>
              <TestTitle>
                <StatusIcon>{result.checklist?.success ? '✅' : '❌'}</StatusIcon>
                تست چک‌لیست
              </TestTitle>
              {result.checklist && (
                <>
                  <MetricRow>
                    <MetricLabel>زمان پاسخ:</MetricLabel>
                    <MetricValue>{result.checklist.responseTime} ms</MetricValue>
                  </MetricRow>
                  {result.checklist.status && (
                    <MetricRow>
                      <MetricLabel>کد وضعیت:</MetricLabel>
                      <MetricValue>{result.checklist.status}</MetricValue>
                    </MetricRow>
                  )}
                  {result.checklist.data?.id && (
                    <MetricRow>
                      <MetricLabel>شناسه چک‌لیست:</MetricLabel>
                      <MetricValue>{result.checklist.data.id}</MetricValue>
                    </MetricRow>
                  )}
                  {result.checklist.error && (
                    <ErrorMessage>خطا: {result.checklist.error}</ErrorMessage>
                  )}
                </>
              )}
            </TestSection>
          </ResultCard>
        );
      })}
    </Container>
  );
}

export default TestResults;