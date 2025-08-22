import React, { useState, useMemo } from 'react';
import styled from 'styled-components';
import { BarChart3, Download, FileText, Calendar, Clock, CheckCircle, XCircle, AlertTriangle, TrendingUp, Filter, Search } from 'lucide-react';
import { TestSession, TestResult, TestStatistics } from '../types';
import { 
  calculateStatistics, 
  exportResults, 
  exportResultsCSV, 
  formatDuration, 
  formatDateTime,
  getStatusColor,
  getAccuracyColor
} from '../utils/helpers';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
`;

const Header = styled.div`
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
  display: flex;
  align-items: center;
  gap: 12px;
`;

const Subtitle = styled.p`
  font-size: 1.125rem;
  color: #64748b;
  margin: 0 0 24px 0;
`;

const ActionButtons = styled.div`
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
`;

const ActionButton = styled.button<{ $variant?: 'primary' | 'secondary' }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: ${props => props.$variant === 'primary' ? 'linear-gradient(135deg, #4f46e5, #7c3aed)' : '#f8fafc'};
  color: ${props => props.$variant === 'primary' ? 'white' : '#374151'};
  border: ${props => props.$variant === 'primary' ? 'none' : '1px solid #e2e8f0'};
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    background: ${props => props.$variant === 'primary' ? 'linear-gradient(135deg, #4338ca, #6d28d9)' : '#f1f5f9'};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }

  svg {
    width: 18px;
    height: 18px;
  }
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
`;

const StatCard = styled.div<{ $variant?: 'success' | 'error' | 'warning' | 'info' }>`
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border-left: 4px solid ${props => {
    switch (props.$variant) {
      case 'success': return '#10b981';
      case 'error': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#6b7280';
    }
  }};
`;

const StatNumber = styled.div`
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 8px;
`;

const StatLabel = styled.div`
  font-size: 0.875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
`;

const Card = styled.div`
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
  display: flex;
  align-items: center;
  gap: 8px;
`;

const SessionCard = styled.div`
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 16px;
  background: white;
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover {
    border-color: #4f46e5;
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.1);
  }
`;

const SessionHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
`;

const SessionInfo = styled.div`
  flex: 1;
`;

const SessionName = styled.h3`
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 8px 0;
`;

const SessionMeta = styled.div`
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
`;

const MetaItem = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.875rem;
  color: #64748b;

  svg {
    width: 16px;
    height: 16px;
  }
`;

const SessionStatus = styled.div<{ $status: string }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  background: ${props => {
    switch (props.$status) {
      case 'completed': return 'rgba(16, 185, 129, 0.1)';
      case 'running': return 'rgba(59, 130, 246, 0.1)';
      case 'failed': return 'rgba(239, 68, 68, 0.1)';
      case 'paused': return 'rgba(245, 158, 11, 0.1)';
      default: return 'rgba(107, 114, 128, 0.1)';
    }
  }};
  color: ${props => {
    switch (props.$status) {
      case 'completed': return '#065f46';
      case 'running': return '#1e40af';
      case 'failed': return '#991b1b';
      case 'paused': return '#92400e';
      default: return '#374151';
    }
  }};
`;

const ResultsTable = styled.div`
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: white;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const TableHeader = styled.th`
  background: #f8fafc;
  padding: 16px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const TableRow = styled.tr`
  &:hover {
    background: #f8fafc;
  }
`;

const TableCell = styled.td`
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
  color: #374151;
  font-size: 0.875rem;
`;

const StatusBadge = styled.span<{ $status: string }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  background: ${props => getStatusColor(props.$status)}20;
  color: ${props => getStatusColor(props.$status)};

  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: ${props => getStatusColor(props.$status)};
  }
`;

const AccuracyBadge = styled.span<{ $accuracy: number }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  background: ${props => getAccuracyColor(props.$accuracy)}20;
  color: ${props => getAccuracyColor(props.$accuracy)};
`;

const FilterBar = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
`;

const FilterSelect = styled.select`
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
  }
`;

const SearchInput = styled.input`
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  flex: 1;
  min-width: 200px;

  &:focus {
    outline: none;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
  }

  &::placeholder {
    color: #9ca3af;
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 48px 24px;
  color: #64748b;
`;

const EmptyIcon = styled.div`
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: #f1f5f9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;

  svg {
    width: 32px;
    height: 32px;
  }
`;

interface ResultsProps {
  sessions: TestSession[];
  onSessionSelect: (session: TestSession) => void;
}

const Results: React.FC<ResultsProps> = ({ sessions, onSessionSelect }) => {
  const [selectedSession, setSelectedSession] = useState<TestSession | null>(
    sessions.length > 0 ? sessions[0] : null
  );
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Calculate overall statistics
  const overallStats = useMemo(() => {
    if (!selectedSession) return null;
    return calculateStatistics(selectedSession.results);
  }, [selectedSession]);

  // Filter results based on current filters
  const filteredResults = useMemo(() => {
    if (!selectedSession) return [];

    return selectedSession.results.filter(result => {
      const matchesStatus = filterStatus === 'all' || result.status === filterStatus;
      const matchesCategory = filterCategory === 'all' || result.endpoint.category === filterCategory;
      const matchesSearch = searchQuery === '' || 
        result.endpoint.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        result.endpoint.path.toLowerCase().includes(searchQuery.toLowerCase());

      return matchesStatus && matchesCategory && matchesSearch;
    });
  }, [selectedSession, filterStatus, filterCategory, searchQuery]);

  // Get unique categories from results
  const categories = useMemo(() => {
    if (!selectedSession) return [];
    const cats = new Set(selectedSession.results.map(r => r.endpoint.category));
    return Array.from(cats).sort();
  }, [selectedSession]);

  const handleExportJSON = () => {
    if (selectedSession) {
      exportResults(selectedSession);
    }
  };

  const handleExportCSV = () => {
    if (selectedSession) {
      exportResultsCSV(selectedSession.results);
    }
  };

  const handleSessionClick = (session: TestSession) => {
    setSelectedSession(session);
    onSessionSelect(session);
  };

  if (sessions.length === 0) {
    return (
      <Container>
        <Header>
          <Title>
            <BarChart3 />
            Test Results & Reports
          </Title>
          <Subtitle>No test sessions available</Subtitle>
        </Header>
        
        <Card>
          <EmptyState>
            <EmptyIcon>
              <FileText />
            </EmptyIcon>
            <h3>No Test Results Yet</h3>
            <p>Run your first API test session to see detailed reports and analytics here.</p>
          </EmptyState>
        </Card>
      </Container>
    );
  }

  return (
    <Container>
      <Header>
        <Title>
          <BarChart3 />
          Test Results & Reports
        </Title>
        <Subtitle>
          Comprehensive analysis and reporting for your API test sessions
        </Subtitle>

        <ActionButtons>
          <ActionButton $variant="primary" onClick={handleExportJSON} disabled={!selectedSession}>
            <Download />
            Export JSON Report
          </ActionButton>
          <ActionButton onClick={handleExportCSV} disabled={!selectedSession}>
            <FileText />
            Export CSV Data
          </ActionButton>
          <ActionButton onClick={() => window.print()}>
            <FileText />
            Print Report
          </ActionButton>
        </ActionButtons>
      </Header>

      {/* Session Selection */}
      <Card>
        <SectionTitle>
          <Calendar />
          Test Sessions ({sessions.length})
        </SectionTitle>

        {sessions.map((session) => (
          <SessionCard 
            key={session.id} 
            onClick={() => handleSessionClick(session)}
            style={{ 
              borderColor: selectedSession?.id === session.id ? '#4f46e5' : '#e2e8f0',
              boxShadow: selectedSession?.id === session.id ? '0 4px 20px rgba(79, 70, 229, 0.1)' : 'none'
            }}
          >
            <SessionHeader>
              <SessionInfo>
                <SessionName>{session.name}</SessionName>
                <SessionMeta>
                  <MetaItem>
                    <Calendar />
                    {formatDateTime(session.startTime)}
                  </MetaItem>
                  <MetaItem>
                    <Clock />
                    {session.endTime ? 
                      formatDuration(session.endTime.getTime() - session.startTime.getTime()) : 
                      'In Progress'
                    }
                  </MetaItem>
                  <MetaItem>
                    <CheckCircle />
                    {session.completedTests}/{session.totalTests} tests
                  </MetaItem>
                </SessionMeta>
              </SessionInfo>
              <SessionStatus $status={session.status}>
                {session.status === 'completed' && <CheckCircle size={16} />}
                {session.status === 'failed' && <XCircle size={16} />}
                {session.status === 'running' && <TrendingUp size={16} />}
                {session.status === 'paused' && <AlertTriangle size={16} />}
                {session.status.charAt(0).toUpperCase() + session.status.slice(1)}
              </SessionStatus>
            </SessionHeader>
          </SessionCard>
        ))}
      </Card>

      {/* Statistics Overview */}
      {selectedSession && overallStats && (
        <Card>
          <SectionTitle>
            <TrendingUp />
            Performance Overview - {selectedSession.name}
          </SectionTitle>

          <StatsGrid>
            <StatCard $variant="info">
              <StatNumber>{overallStats.totalRequests}</StatNumber>
              <StatLabel>Total Requests</StatLabel>
            </StatCard>
            <StatCard $variant="success">
              <StatNumber>{overallStats.successRate.toFixed(1)}%</StatNumber>
              <StatLabel>Success Rate</StatLabel>
            </StatCard>
            <StatCard $variant="warning">
              <StatNumber>{formatDuration(overallStats.averageResponseTime)}</StatNumber>
              <StatLabel>Avg Response Time</StatLabel>
            </StatCard>
            <StatCard $variant="error">
              <StatNumber>{overallStats.errorRate.toFixed(1)}%</StatNumber>
              <StatLabel>Error Rate</StatLabel>
            </StatCard>
            <StatCard>
              <StatNumber>{overallStats.throughput.toFixed(2)}</StatNumber>
              <StatLabel>Requests/Second</StatLabel>
            </StatCard>
            <StatCard>
              <StatNumber>{formatDuration(overallStats.minResponseTime)} - {formatDuration(overallStats.maxResponseTime)}</StatNumber>
              <StatLabel>Response Time Range</StatLabel>
            </StatCard>
          </StatsGrid>
        </Card>
      )}

      {/* Detailed Results Table */}
      {selectedSession && (
        <Card>
          <SectionTitle>
            <FileText />
            Detailed Test Results ({filteredResults.length} of {selectedSession.results.length})
          </SectionTitle>

          <FilterBar>
            <FilterSelect 
              value={filterStatus} 
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
              <option value="timeout">Timeout</option>
            </FilterSelect>

            <FilterSelect 
              value={filterCategory} 
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <option value="all">All Categories</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </FilterSelect>

            <SearchInput
              type="text"
              placeholder="Search endpoints..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search size={16} style={{ color: '#9ca3af', marginLeft: '-32px' }} />
          </FilterBar>

          <ResultsTable>
            <Table>
              <thead>
                <tr>
                  <TableHeader>Endpoint</TableHeader>
                  <TableHeader>Method</TableHeader>
                  <TableHeader>Category</TableHeader>
                  <TableHeader>Status</TableHeader>
                  <TableHeader>Response Time</TableHeader>
                  <TableHeader>Status Code</TableHeader>
                  <TableHeader>Accuracy</TableHeader>
                  <TableHeader>Timestamp</TableHeader>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((result) => (
                  <TableRow key={result.id}>
                    <TableCell>
                      <div>
                        <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                          {result.endpoint.name}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {result.endpoint.path}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span style={{ 
                        fontFamily: 'monospace', 
                        fontSize: '0.75rem',
                        padding: '2px 6px',
                        background: '#f1f5f9',
                        borderRadius: '4px'
                      }}>
                        {result.endpoint.method}
                      </span>
                    </TableCell>
                    <TableCell>{result.endpoint.category}</TableCell>
                    <TableCell>
                      <StatusBadge $status={result.status}>
                        {result.status}
                      </StatusBadge>
                    </TableCell>
                    <TableCell>{formatDuration(result.totalTime)}</TableCell>
                    <TableCell>
                      {result.statusCode && (
                        <span style={{
                          color: result.statusCode >= 200 && result.statusCode < 300 ? '#10b981' : '#ef4444'
                        }}>
                          {result.statusCode}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {result.accuracyPercentage !== undefined && (
                        <AccuracyBadge $accuracy={result.accuracyPercentage}>
                          {result.accuracyPercentage.toFixed(1)}%
                        </AccuracyBadge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div style={{ fontSize: '0.75rem' }}>
                        {formatDateTime(result.timestamp)}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </tbody>
            </Table>
          </ResultsTable>

          {filteredResults.length === 0 && (
            <EmptyState>
              <p>No results match your current filters.</p>
            </EmptyState>
          )}
        </Card>
      )}

      {/* Category Breakdown */}
      {selectedSession && overallStats && Object.keys(overallStats.categoriesStats).length > 0 && (
        <Card>
          <SectionTitle>
            <Filter />
            Performance by Category
          </SectionTitle>

          <div style={{ display: 'grid', gap: '16px' }}>
            {Object.entries(overallStats.categoriesStats).map(([category, stats]) => (
              <div key={category} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: '4px' }}>{category}</div>
                  <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                    {stats.total} endpoints • {stats.successful} successful • {stats.failed} failed
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: '600', color: '#4f46e5' }}>
                    {formatDuration(stats.averageTime)}
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                    avg response time
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </Container>
  );
};

export default Results;