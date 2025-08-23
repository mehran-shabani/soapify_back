import { TestResult, TestStatistics, ResumeData, TestSession } from '../types';

// Generate unique IDs
export const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Format time duration
export const formatDuration = (milliseconds: number): string => {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  }
  
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

// Format file size
export const formatFileSize = (bytes: number): string => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 Bytes';
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
};

// Format date and time
export const formatDateTime = (date: Date): string => {
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// Calculate response accuracy percentage
export const calculateResponseAccuracy = (expected: any, actual: any): number => {
  if (typeof expected !== typeof actual) {
    return 0;
  }

  if (typeof expected === 'string') {
    return expected === actual ? 100 : 0;
  }

  if (typeof expected === 'number') {
    return expected === actual ? 100 : 0;
  }

  if (typeof expected === 'boolean') {
    return expected === actual ? 100 : 0;
  }

  if (Array.isArray(expected) && Array.isArray(actual)) {
    if (expected.length !== actual.length) {
      return Math.max(0, 100 - Math.abs(expected.length - actual.length) * 10);
    }

    let matches = 0;
    for (let i = 0; i < expected.length; i++) {
      if (calculateResponseAccuracy(expected[i], actual[i]) > 50) {
        matches++;
      }
    }
    return (matches / expected.length) * 100;
  }

  if (typeof expected === 'object' && expected !== null && actual !== null) {
    const expectedKeys = Object.keys(expected);
    const actualKeys = Object.keys(actual);
    
    // Check if all expected keys exist
    const missingKeys = expectedKeys.filter(key => !actualKeys.includes(key));
    const extraKeys = actualKeys.filter(key => !expectedKeys.includes(key));
    
    let totalScore = 0;
    let totalFields = expectedKeys.length;

    for (const key of expectedKeys) {
      if (key in actual) {
        totalScore += calculateResponseAccuracy(expected[key], actual[key]);
      }
    }

    // Penalize for missing or extra keys
    const penalty = (missingKeys.length + extraKeys.length) * 5;
    const averageScore = totalFields > 0 ? totalScore / totalFields : 0;
    
    return Math.max(0, averageScore - penalty);
  }

  return 0;
};

// Calculate test statistics
export const calculateStatistics = (results: TestResult[]): TestStatistics => {
  if (results.length === 0) {
    return {
      totalRequests: 0,
      successRate: 0,
      averageResponseTime: 0,
      minResponseTime: 0,
      maxResponseTime: 0,
      errorRate: 0,
      throughput: 0,
      categoriesStats: {}
    };
  }

  const successful = results.filter(r => r.status === 'success');
  const responseTimes = results.map(r => r.totalTime);
  
  // Calculate session duration
  const startTime = Math.min(...results.map(r => r.timestamp.getTime()));
  const endTime = Math.max(...results.map(r => r.timestamp.getTime()));
  const sessionDuration = (endTime - startTime) / 1000; // in seconds

  // Calculate category statistics
  const categoriesStats: Record<string, any> = {};
  results.forEach(result => {
    const category = result.endpoint.category;
    if (!categoriesStats[category]) {
      categoriesStats[category] = {
        total: 0,
        successful: 0,
        failed: 0,
        totalTime: 0
      };
    }
    
    categoriesStats[category].total++;
    categoriesStats[category].totalTime += result.totalTime;
    
    if (result.status === 'success') {
      categoriesStats[category].successful++;
    } else {
      categoriesStats[category].failed++;
    }
  });

  // Calculate averages for categories
  Object.keys(categoriesStats).forEach(category => {
    const stats = categoriesStats[category];
    stats.averageTime = stats.total > 0 ? stats.totalTime / stats.total : 0;
  });

  return {
    totalRequests: results.length,
    successRate: (successful.length / results.length) * 100,
    averageResponseTime: responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length,
    minResponseTime: Math.min(...responseTimes),
    maxResponseTime: Math.max(...responseTimes),
    errorRate: ((results.length - successful.length) / results.length) * 100,
    throughput: sessionDuration > 0 ? results.length / sessionDuration : 0,
    categoriesStats
  };
};

// Save session data for resume functionality
export const saveResumeData = (sessionId: string, lastCompletedIndex: number, config: any, partialResults: TestResult[]): void => {
  const resumeData: ResumeData = {
    sessionId,
    lastCompletedIndex,
    timestamp: new Date(),
    config,
    partialResults
  };

  try {
    localStorage.setItem(`resume_${sessionId}`, JSON.stringify(resumeData));
    localStorage.setItem('last_session_id', sessionId);
  } catch (error) {
    console.error('Failed to save resume data:', error);
  }
};

// Load resume data
export const loadResumeData = (sessionId?: string): ResumeData | null => {
  try {
    const targetSessionId = sessionId || localStorage.getItem('last_session_id');
    if (!targetSessionId) return null;

    const data = localStorage.getItem(`resume_${targetSessionId}`);
    if (!data) return null;

    const resumeData = JSON.parse(data);
    return {
      ...resumeData,
      timestamp: new Date(resumeData.timestamp)
    };
  } catch (error) {
    console.error('Failed to load resume data:', error);
    return null;
  }
};

// Clear resume data
export const clearResumeData = (sessionId: string): void => {
  try {
    localStorage.removeItem(`resume_${sessionId}`);
    if (localStorage.getItem('last_session_id') === sessionId) {
      localStorage.removeItem('last_session_id');
    }
  } catch (error) {
    console.error('Failed to clear resume data:', error);
  }
};

// Export test results to JSON
export const exportResults = (session: TestSession): void => {
  const exportData = {
    session: {
      ...session,
      results: session.results.map(result => ({
        ...result,
        timestamp: result.timestamp.toISOString()
      }))
    },
    statistics: calculateStatistics(session.results),
    exportedAt: new Date().toISOString()
  };

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `api_test_results_${session.id}_${new Date().toISOString().split('T')[0]}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// Export results to CSV
export const exportResultsCSV = (results: TestResult[]): void => {
  const headers = [
    'Timestamp',
    'Endpoint Name',
    'Method',
    'Path',
    'Category',
    'Status',
    'Status Code',
    'Request Time (ms)',
    'Response Time (ms)',
    'Total Time (ms)',
    'Request Size (bytes)',
    'Response Size (bytes)',
    'Accuracy (%)',
    'Error Message'
  ];

  const csvData = [
    headers.join(','),
    ...results.map(result => [
      result.timestamp.toISOString(),
      `"${result.endpoint.name}"`,
      result.endpoint.method,
      `"${result.endpoint.path}"`,
      `"${result.endpoint.category}"`,
      result.status,
      result.statusCode || '',
      result.requestTime,
      result.responseTime,
      result.totalTime,
      result.requestSize || 0,
      result.responseSize || 0,
      result.accuracyPercentage || 0,
      `"${result.error || ''}"`
    ].join(','))
  ].join('\n');

  const blob = new Blob([csvData], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `api_test_results_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

// Deep clone object
export const deepClone = <T>(obj: T): T => {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T;
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as unknown as T;
  if (typeof obj === 'object') {
    const cloned = {} as T;
    Object.keys(obj).forEach(key => {
      (cloned as any)[key] = deepClone((obj as any)[key]);
    });
    return cloned;
  }
  return obj;
};

// Debounce function
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(null, args), wait);
  };
};

// Throttle function
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func.apply(null, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// Get status color for UI
export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'success':
      return '#10b981'; // green
    case 'error':
      return '#ef4444'; // red
    case 'timeout':
      return '#f59e0b'; // yellow
    case 'pending':
      return '#6b7280'; // gray
    default:
      return '#6b7280';
  }
};

// Get accuracy color for UI
export const getAccuracyColor = (accuracy: number): string => {
  if (accuracy >= 90) return '#10b981'; // green
  if (accuracy >= 70) return '#f59e0b'; // yellow
  if (accuracy >= 50) return '#f97316'; // orange
  return '#ef4444'; // red
};

// Validate URL
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

// Generate test data for endpoints that need payload
export const generateTestPayload = (endpoint: any): any => {
  if (!endpoint.payload) return undefined;

  const payload: any = {};
  
  Object.keys(endpoint.payload).forEach(key => {
    const type = endpoint.payload[key];
    
    switch (type) {
      case 'string':
        payload[key] = `test_${key}_${Date.now()}`;
        break;
      case 'number':
        payload[key] = Math.floor(Math.random() * 100);
        break;
      case 'boolean':
        payload[key] = Math.random() > 0.5;
        break;
      case 'array':
        payload[key] = [`test_item_${Date.now()}`];
        break;
      case 'object':
        payload[key] = { test: 'data' };
        break;
      case 'file':
        // For file uploads, we'll need special handling
        payload[key] = new Blob(['test file content'], { type: 'text/plain' });
        break;
      default:
        payload[key] = `test_${type}_${Date.now()}`;
    }
  });

  return payload;
};