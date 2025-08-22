import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://django-m.chbk.app';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Request interceptor to add auth token if needed
api.interceptors.request.use(
  (config) => {
    // Add timestamp to track request time
    config.metadata = { startTime: new Date() };
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to calculate response time
api.interceptors.response.use(
  (response) => {
    const endTime = new Date();
    const startTime = response.config.metadata.startTime;
    response.responseTime = endTime - startTime;
    return response;
  },
  (error) => {
    if (error.response) {
      const endTime = new Date();
      const startTime = error.config.metadata.startTime;
      error.response.responseTime = endTime - startTime;
    }
    return Promise.reject(error);
  }
);

// Voice upload service
export const voiceService = {
  async uploadAudio(audioBlob, metadata = {}) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('title', metadata.title || 'Test Recording');
    formData.append('description', metadata.description || 'API Test Recording');

    const response = await api.post('/api/v1/voice/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      }
    });

    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status,
      fileSize: audioBlob.size
    };
  },

  async getRecordings() {
    const response = await api.get('/api/v1/voice/');
    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  }
};

// STT service
export const sttService = {
  async transcribe(audioUrl, language = 'fa') {
    const response = await api.post('/api/v1/stt/transcribe/', {
      audio_url: audioUrl,
      language: language
    });

    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  },

  async transcribeFile(audioBlob, language = 'fa') {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('language', language);

    const response = await api.post('/api/v1/stt/transcribe-file/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      }
    });

    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  }
};

// Checklist service
export const checklistService = {
  async create(checklist) {
    const response = await api.post('/api/v1/checklists/', checklist);
    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  },

  async getAll() {
    const response = await api.get('/api/v1/checklists/');
    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  },

  async getById(id) {
    const response = await api.get(`/api/v1/checklists/${id}/`);
    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  },

  async update(id, checklist) {
    const response = await api.put(`/api/v1/checklists/${id}/`, checklist);
    return {
      success: true,
      data: response.data,
      responseTime: response.responseTime,
      status: response.status
    };
  },

  async delete(id) {
    const response = await api.delete(`/api/v1/checklists/${id}/`);
    return {
      success: true,
      responseTime: response.responseTime,
      status: response.status
    };
  }
};

// Test runner service
export const testRunner = {
  async runAllTests() {
    const results = {
      voice: null,
      stt: null,
      checklist: null,
      timestamp: new Date().toISOString()
    };

    try {
      // Test voice upload with a dummy audio
      const dummyAudio = new Blob(['dummy'], { type: 'audio/wav' });
      results.voice = await voiceService.uploadAudio(dummyAudio).catch(err => ({
        success: false,
        error: err.message,
        responseTime: err.response?.responseTime || 0
      }));

      // Test STT
      if (results.voice?.success && results.voice.data?.audio_url) {
        results.stt = await sttService.transcribe(results.voice.data.audio_url).catch(err => ({
          success: false,
          error: err.message,
          responseTime: err.response?.responseTime || 0
        }));
      }

      // Test checklist
      const testChecklist = {
        title: `Test Checklist ${Date.now()}`,
        items: [
          { text: 'Test item 1', completed: false },
          { text: 'Test item 2', completed: true }
        ]
      };
      results.checklist = await checklistService.create(testChecklist).catch(err => ({
        success: false,
        error: err.message,
        responseTime: err.response?.responseTime || 0
      }));

    } catch (error) {
      console.error('Test runner error:', error);
    }

    return results;
  },

  async runLoadTest(service, method, iterations = 10) {
    const results = [];
    const promises = [];

    for (let i = 0; i < iterations; i++) {
      let promise;
      
      switch (service) {
        case 'checklist':
          promise = checklistService[method]({
            title: `Load Test ${i}`,
            items: [{ text: 'Test', completed: false }]
          });
          break;
        case 'voice':
          const blob = new Blob(['test'], { type: 'audio/wav' });
          promise = voiceService[method](blob);
          break;
        default:
          promise = Promise.reject(new Error('Unknown service'));
      }

      promises.push(
        promise
          .then(result => ({ ...result, index: i }))
          .catch(err => ({ 
            success: false, 
            error: err.message, 
            index: i,
            responseTime: err.response?.responseTime || 0
          }))
      );
    }

    const allResults = await Promise.all(promises);
    
    // Calculate statistics
    const successCount = allResults.filter(r => r.success).length;
    const responseTimes = allResults
      .filter(r => r.responseTime)
      .map(r => r.responseTime);
    
    const stats = {
      totalRequests: iterations,
      successfulRequests: successCount,
      failedRequests: iterations - successCount,
      successRate: (successCount / iterations) * 100,
      responseTimes: {
        min: Math.min(...responseTimes),
        max: Math.max(...responseTimes),
        avg: responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length,
        median: responseTimes.sort((a, b) => a - b)[Math.floor(responseTimes.length / 2)]
      }
    };

    return { results: allResults, stats };
  }
};

export default api;