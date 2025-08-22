import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { ApiEndpoint, TestResult, TestConfig } from '../types';
import { generateId, calculateResponseAccuracy } from '../utils/helpers';

export class ApiService {
  private config: TestConfig;
  private abortController?: AbortController;

  constructor(config: TestConfig) {
    this.config = config;
  }

  updateConfig(config: TestConfig) {
    this.config = config;
  }

  async testEndpoint(endpoint: ApiEndpoint): Promise<TestResult> {
    const testId = generateId();
    const startTime = Date.now();
    let requestTime = 0;
    let responseTime = 0;
    let totalTime = 0;

    const result: TestResult = {
      id: testId,
      endpoint,
      timestamp: new Date(),
      requestTime: 0,
      responseTime: 0,
      totalTime: 0,
      status: 'pending'
    };

    try {
      // Create abort controller for this request
      this.abortController = new AbortController();

      // Build request configuration
      const requestConfig = this.buildRequestConfig(endpoint);
      
      // Measure request preparation time
      const requestPrepTime = Date.now();
      requestTime = requestPrepTime - startTime;

      // Make the actual request
      const response = await this.makeRequest(requestConfig);
      
      // Measure response processing time
      const responseEndTime = Date.now();
      responseTime = responseEndTime - requestPrepTime;
      totalTime = responseEndTime - startTime;

      // Process successful response
      result.requestTime = requestTime;
      result.responseTime = responseTime;
      result.totalTime = totalTime;
      result.status = 'success';
      result.statusCode = response.status;
      result.response = response.data;
      result.actualResponse = response.data;
      result.requestSize = this.calculateRequestSize(requestConfig);
      result.responseSize = this.calculateResponseSize(response);

      // Calculate accuracy if expected response is provided
      if (endpoint.expected_response) {
        result.expectedResponse = endpoint.expected_response;
        result.accuracyPercentage = calculateResponseAccuracy(
          endpoint.expected_response,
          response.data
        );
      }

    } catch (error) {
      const errorEndTime = Date.now();
      totalTime = errorEndTime - startTime;
      
      result.totalTime = totalTime;
      result.requestTime = requestTime;
      result.responseTime = errorEndTime - (startTime + requestTime);
      result.status = 'error';

      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        result.statusCode = axiosError.response?.status;
        result.error = axiosError.message;
        result.response = axiosError.response?.data;
        
        // Handle timeout specifically
        if (axiosError.code === 'ECONNABORTED') {
          result.status = 'timeout';
        }
      } else {
        result.error = error instanceof Error ? error.message : 'Unknown error';
      }
    }

    return result;
  }

  async testMultipleEndpoints(
    endpoints: ApiEndpoint[],
    onProgress?: (progress: number, result: TestResult) => void,
    onComplete?: (results: TestResult[]) => void
  ): Promise<TestResult[]> {
    const results: TestResult[] = [];
    const concurrency = this.config.concurrency || 1;

    if (concurrency === 1) {
      // Sequential execution
      for (let i = 0; i < endpoints.length; i++) {
        const result = await this.testEndpoint(endpoints[i]);
        results.push(result);
        
        if (onProgress) {
          onProgress(((i + 1) / endpoints.length) * 100, result);
        }
      }
    } else {
      // Concurrent execution
      const chunks = this.chunkArray(endpoints, concurrency);
      
      for (const chunk of chunks) {
        const chunkPromises = chunk.map(endpoint => this.testEndpoint(endpoint));
        const chunkResults = await Promise.all(chunkPromises);
        
        results.push(...chunkResults);
        
        if (onProgress) {
          onProgress((results.length / endpoints.length) * 100, chunkResults[chunkResults.length - 1]);
        }
      }
    }

    if (onComplete) {
      onComplete(results);
    }

    return results;
  }

  async testWithRetries(endpoint: ApiEndpoint, maxRetries?: number): Promise<TestResult> {
    const retries = maxRetries || this.config.retries || 1;
    let lastResult: TestResult | null = null;

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const result = await this.testEndpoint(endpoint);
        
        if (result.status === 'success') {
          return result;
        }
        
        lastResult = result;
        
        // Wait before retry (exponential backoff)
        if (attempt < retries) {
          await this.delay(Math.pow(2, attempt) * 1000);
        }
        
      } catch (error) {
        if (attempt === retries) {
          throw error;
        }
        await this.delay(Math.pow(2, attempt) * 1000);
      }
    }

    return lastResult || {
      id: generateId(),
      endpoint,
      timestamp: new Date(),
      requestTime: 0,
      responseTime: 0,
      totalTime: 0,
      status: 'error',
      error: 'All retry attempts failed'
    };
  }

  cancelCurrentRequests() {
    if (this.abortController) {
      this.abortController.abort();
    }
  }

  private buildRequestConfig(endpoint: ApiEndpoint): AxiosRequestConfig {
    const config: AxiosRequestConfig = {
      method: endpoint.method,
      url: `${this.config.baseUrl}${endpoint.path}`,
      timeout: this.config.timeout || 30000,
      signal: this.abortController?.signal,
      headers: {
        'Content-Type': 'application/json',
        ...this.config.customHeaders,
        ...endpoint.headers
      }
    };

    // Add authentication if required
    if (endpoint.auth_required && this.config.authToken) {
      config.headers!['Authorization'] = `Bearer ${this.config.authToken}`;
    }

    // Add request body for non-GET requests
    if (endpoint.method !== 'GET' && endpoint.payload) {
      config.data = endpoint.payload;
    }

    // Add query parameters
    if (endpoint.query_params) {
      config.params = endpoint.query_params;
    }

    return config;
  }

  private async makeRequest(config: AxiosRequestConfig): Promise<AxiosResponse> {
    return axios(config);
  }

  private calculateRequestSize(config: AxiosRequestConfig): number {
    let size = 0;
    
    // Headers size
    if (config.headers) {
      size += JSON.stringify(config.headers).length;
    }
    
    // Body size
    if (config.data) {
      size += JSON.stringify(config.data).length;
    }
    
    // URL and params size
    size += (config.url || '').length;
    if (config.params) {
      size += JSON.stringify(config.params).length;
    }

    return size;
  }

  private calculateResponseSize(response: AxiosResponse): number {
    let size = 0;
    
    // Headers size
    if (response.headers) {
      size += JSON.stringify(response.headers).length;
    }
    
    // Body size
    if (response.data) {
      size += JSON.stringify(response.data).length;
    }

    return size;
  }

  private chunkArray<T>(array: T[], chunkSize: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

export default ApiService;