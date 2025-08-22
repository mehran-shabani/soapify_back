import axios from 'axios';

// Server monitoring URL - can be configured via environment variable
const SERVER_MONITOR_URL = process.env.REACT_APP_SERVER_MONITOR_URL || 'http://localhost:8080';

// Create axios instance for server communication
const serverApi = axios.create({
  baseURL: SERVER_MONITOR_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

export const serverSync = {
  /**
   * Trigger a test on the server
   */
  async triggerServerTest(testType, params = {}) {
    try {
      const response = await serverApi.post('/api/webhook/trigger-test', {
        test_type: testType,
        params
      });
      return response.data;
    } catch (error) {
      console.error('Failed to trigger server test:', error);
      throw error;
    }
  },

  /**
   * Check the status of a running test
   */
  async checkTestStatus() {
    try {
      const response = await serverApi.get('/api/webhook/test-status');
      return response.data;
    } catch (error) {
      console.error('Failed to check test status:', error);
      throw error;
    }
  },

  /**
   * Send frontend results to server and get synchronized results
   */
  async syncTestResults(testId, frontendResults) {
    try {
      const response = await serverApi.post('/api/webhook/sync-test', {
        frontend_test_id: testId,
        frontend_results: frontendResults
      });
      return response.data;
    } catch (error) {
      console.error('Failed to sync test results:', error);
      throw error;
    }
  },

  /**
   * Poll server test status until completion
   */
  async waitForServerTest(maxAttempts = 60, delayMs = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      const status = await this.checkTestStatus();
      
      if (!status.in_progress) {
        return status;
      }
      
      // Wait before next check
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
    
    throw new Error('Server test timeout');
  },

  /**
   * Run synchronized tests - both frontend and server
   */
  async runSynchronizedTests(frontendTestRunner) {
    const testId = `sync-${Date.now()}`;
    
    // Run frontend tests
    const frontendResults = await frontendTestRunner();
    
    // Send to server for synchronized testing
    const syncResults = await this.syncTestResults(testId, frontendResults);
    
    return {
      testId,
      frontend: frontendResults,
      server: syncResults.server,
      comparison: syncResults.comparison,
      timestamp: new Date().toISOString()
    };
  },

  /**
   * Get server system metrics
   */
  async getServerMetrics() {
    try {
      const response = await serverApi.get('/api/metrics/system');
      return response.data;
    } catch (error) {
      console.error('Failed to get server metrics:', error);
      throw error;
    }
  },

  /**
   * Get server performance metrics
   */
  async getPerformanceMetrics(hours = 24) {
    try {
      const response = await serverApi.get(`/api/metrics/performance?hours=${hours}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get performance metrics:', error);
      throw error;
    }
  },

  /**
   * Get server alerts
   */
  async getServerAlerts() {
    try {
      const response = await serverApi.get('/api/alerts');
      return response.data;
    } catch (error) {
      console.error('Failed to get server alerts:', error);
      throw error;
    }
  }
};

// Helper function to run parallel tests
export async function runParallelTests(testRunner, serverTestType, serverParams = {}) {
  const results = {
    frontend: null,
    server: null,
    startTime: Date.now(),
    endTime: null
  };

  try {
    // Start both tests in parallel
    const [frontendResult, serverTrigger] = await Promise.all([
      testRunner(),
      serverSync.triggerServerTest(serverTestType, serverParams)
    ]);

    results.frontend = frontendResult;

    // Wait for server test to complete
    const serverStatus = await serverSync.waitForServerTest();
    results.server = serverStatus.latest_results;

  } catch (error) {
    console.error('Parallel test error:', error);
    results.error = error.message;
  }

  results.endTime = Date.now();
  results.totalTime = results.endTime - results.startTime;

  return results;
}

export default serverSync;