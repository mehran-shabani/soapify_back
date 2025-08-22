# Soapify API Tester - Unified Testing Platform

A comprehensive, unified React-based API testing application for the Soapify project with real-time audio recording capabilities.

## 🚀 Features

### Core API Testing
- **Comprehensive Endpoint Coverage**: Tests all 70+ API endpoints across 12 categories
- **Multiple Request Methods**: Support for GET, POST, PUT, DELETE, PATCH requests
- **Real-time Performance Metrics**: Request/response timing, throughput analysis
- **Response Validation**: Automatic accuracy percentage calculation
- **Robust Error Handling**: Graceful handling of timeouts, network errors, and unexpected responses

### Advanced Capabilities
- **Resume Functionality**: Automatically resume interrupted test sessions
- **Real-time Audio Recording**: Persistent audio recording during test sessions
- **Export & Analytics**: Export results to JSON/CSV, detailed performance analytics
- **Session Management**: Create, pause, resume, and manage multiple test sessions
- **Live Dashboard**: Real-time monitoring of test progress and system health

### Audio Recording Features
- **Persistent Recording**: Continuous audio capture during API testing
- **Multiple Formats**: Support for WAV, MP3, M4A formats
- **Real-time Controls**: Start, pause, resume, stop recording capabilities
- **Session Linking**: Audio recordings linked to specific test sessions
- **Storage Management**: Local storage with automatic cleanup

## 📁 Project Structure

```
api_check/
├── soapify-api-tester/           # Unified React Application
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── Dashboard.tsx     # Main dashboard
│   │   │   ├── TestRunner.tsx    # Test execution engine
│   │   │   ├── AudioRecorder.tsx # Audio recording interface
│   │   │   ├── Results.tsx       # Results and analytics
│   │   │   └── Settings.tsx      # Configuration panel
│   │   ├── services/            # Core services
│   │   │   ├── apiService.ts    # API testing logic
│   │   │   └── audioService.ts  # Audio recording service
│   │   ├── types/               # TypeScript definitions
│   │   └── utils/               # Helper utilities
│   ├── public/
│   └── package.json
├── api_endpoints_checklist.json  # Complete API endpoint catalog
├── README.md                     # This file
└── start-testing.sh             # Quick start script
```

## 🛠 Installation & Setup

### Prerequisites
- Node.js 16+ and npm
- Modern web browser with microphone access
- Network access to Soapify API server

### Quick Start

1. **Install Dependencies**
   ```bash
   cd soapify-api-tester
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm start
   ```

3. **Access Application**
   - Open http://localhost:3000
   - Grant microphone permissions when prompted

### Production Build

```bash
npm run build
npm run serve
```

## 📊 API Endpoint Coverage

The application tests **70+ endpoints** across these categories:

- **Authentication & JWT** (3 endpoints)
- **Accounts** (7 endpoints)
- **Encounters** (5 endpoints)
- **Speech-to-Text** (10 endpoints)
- **NLP Processing** (5 endpoints)
- **Outputs** (6 endpoints)
- **Uploads** (6 endpoints)
- **Integrations** (9 endpoints)
- **Checklist** (6 endpoints)
- **Search** (4 endpoints)
- **Analytics** (9 endpoints)
- **Embeddings** (1 endpoint)
- **System** (1 endpoint)

## 🎯 Key Features Explained

### 1. Multiple Request Methods Testing
- Automatically detects appropriate HTTP methods for each endpoint
- Generates realistic test payloads based on endpoint specifications
- Supports file uploads and complex data structures

### 2. Timing Measurements
- **Request Time**: Time to prepare and send request
- **Response Time**: Time to receive and process response
- **Total Time**: End-to-end request duration
- **Throughput**: Requests per second analysis

### 3. Response Validation
- Compares actual responses with expected response schemas
- Calculates accuracy percentage for data validation
- Identifies missing fields, extra data, and type mismatches

### 4. Error Handling
- **Network Errors**: Connection timeouts, DNS failures
- **HTTP Errors**: 4xx/5xx status codes with detailed messages
- **Validation Errors**: Response format mismatches
- **Recovery**: Automatic retry with exponential backoff

### 5. Resume Functionality
- Automatically saves progress during test execution
- Resumes from last completed endpoint on restart
- Preserves partial results and configuration
- Works across browser sessions

### 6. Real-time Audio Recording
- **Persistent Recording**: Continues recording during entire test session
- **Real-time Monitoring**: Live duration display and status indicators
- **Quality Settings**: Configurable sample rates and formats
- **Storage Management**: Automatic local storage with size limits

## 🔧 Configuration Options

### API Testing Configuration
```typescript
{
  baseUrl: 'https://django-m.chbk.app',
  timeout: 30000,              // Request timeout (ms)
  retries: 1,                  // Retry attempts
  concurrency: 1,              // Parallel requests
  authToken: 'jwt-token',      // Authentication token
  validateResponses: true,     // Enable response validation
  saveResults: true,           // Save results locally
  resumeOnFailure: true        // Enable resume functionality
}
```

### Audio Recording Configuration
```typescript
{
  enableAudioRecording: true,
  audioFormat: 'wav',          // wav, mp3, m4a
  sampleRate: 44100,           // Audio quality
  echoCancellation: true,      // Noise reduction
  noiseSuppression: true       // Audio enhancement
}
```

## 📈 Analytics & Reporting

### Performance Metrics
- Success rate percentage
- Average response times
- Min/max response times
- Error rate analysis
- Throughput measurements

### Category-wise Statistics
- Performance by API category
- Success rates per category
- Response time distributions
- Error patterns analysis

### Export Options
- **JSON Export**: Complete session data with metadata
- **CSV Export**: Tabular data for spreadsheet analysis
- **Audio Downloads**: Recorded audio files
- **Performance Reports**: Detailed analytics summaries

## 🎮 Usage Guide

### Starting a Test Session

1. **Dashboard**: View API overview and system status
2. **Quick Start**: Launch immediate test of all endpoints
3. **Custom Selection**: Choose specific endpoints or categories
4. **Configuration**: Adjust timeout, retries, audio settings

### During Test Execution

1. **Real-time Progress**: Watch tests execute with live updates
2. **Audio Recording**: Monitor recording status and duration
3. **Pause/Resume**: Control test execution as needed
4. **Error Monitoring**: View errors and retry attempts

### After Test Completion

1. **Results Analysis**: Review success rates and performance
2. **Export Data**: Download results in preferred format
3. **Audio Review**: Listen to recorded audio sessions
4. **Historical Comparison**: Compare with previous test runs

## 🚨 Troubleshooting

### Common Issues

**Microphone Access Denied**
- Enable microphone permissions in browser settings
- Ensure HTTPS connection for audio recording
- Check browser compatibility (Chrome, Firefox recommended)

**API Connection Failures**
- Verify base URL configuration
- Check network connectivity
- Validate authentication tokens

**Performance Issues**
- Reduce concurrency level
- Increase timeout values
- Check system resources

### Browser Compatibility

- **Chrome**: Full support (recommended)
- **Firefox**: Full support
- **Safari**: Limited audio recording support
- **Edge**: Full support

## 🔒 Security & Privacy

- **Local Storage**: All data stored locally in browser
- **No External Services**: Audio recording stays on device
- **Secure Connections**: HTTPS required for audio features
- **Data Cleanup**: Automatic cleanup of old recordings

## 🤝 Contributing

This is an internal testing tool for the Soapify project. For issues or improvements:

1. Test the application thoroughly
2. Document any bugs or enhancement requests
3. Provide detailed reproduction steps
4. Include browser and system information

## 📝 License

Internal tool for Soapify project - All rights reserved.

---

**Base URL**: https://django-m.chbk.app/
**Version**: 1.0.0
**Last Updated**: December 2024