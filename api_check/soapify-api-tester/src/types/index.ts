export interface ApiEndpoint {
  name: string;
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  description: string;
  category: string;
  auth_required?: boolean;
  payload?: Record<string, any>;
  query_params?: Record<string, any>;
  expected_response?: Record<string, any> | string;
  headers?: Record<string, string>;
}

export interface TestResult {
  id: string;
  endpoint: ApiEndpoint;
  timestamp: Date;
  requestTime: number;
  responseTime: number;
  totalTime: number;
  status: 'success' | 'error' | 'timeout' | 'pending';
  statusCode?: number;
  response?: any;
  error?: string;
  expectedResponse?: any;
  actualResponse?: any;
  accuracyPercentage?: number;
  requestSize?: number;
  responseSize?: number;
}

export interface TestSession {
  id: string;
  name: string;
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'paused' | 'failed';
  totalTests: number;
  completedTests: number;
  successfulTests: number;
  failedTests: number;
  results: TestResult[];
  config: TestConfig;
}

export interface TestConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
  concurrency: number;
  authToken?: string;
  customHeaders?: Record<string, string>;
  enableAudioRecording: boolean;
  audioFormat: 'wav' | 'mp3' | 'm4a';
  testMethods: string[];
  validateResponses: boolean;
  saveResults: boolean;
  resumeOnFailure: boolean;
}

export interface AudioRecording {
  id: string;
  sessionId: string;
  startTime: Date;
  endTime?: Date;
  duration?: number;
  format: string;
  size?: number;
  blob?: Blob;
  url?: string;
  transcription?: string;
}

export interface TestScenario {
  name: string;
  description: string;
  steps: string[];
  endpoints: ApiEndpoint[];
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: Date;
  services: {
    api: boolean;
    database: boolean;
    storage: boolean;
    authentication: boolean;
  };
  metrics: {
    responseTime: number;
    errorRate: number;
    throughput: number;
  };
}

export interface TestStatistics {
  totalRequests: number;
  successRate: number;
  averageResponseTime: number;
  minResponseTime: number;
  maxResponseTime: number;
  errorRate: number;
  throughput: number;
  categoriesStats: Record<string, {
    total: number;
    successful: number;
    failed: number;
    averageTime: number;
  }>;
}

export interface ResumeData {
  sessionId: string;
  lastCompletedIndex: number;
  timestamp: Date;
  config: TestConfig;
  partialResults: TestResult[];
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'debug';
  category: string;
  message: string;
  data?: any;
  sessionId?: string;
}