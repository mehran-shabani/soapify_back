# SOAPify - AI-Powered Medical Documentation System

SOAPify is a comprehensive medical documentation system that uses AI to transform doctor-patient conversations into structured SOAP notes.

## 🌟 Key Features

- **Speech-to-Text**: Convert audio recordings to accurate transcripts using Whisper AI
- **AI-Powered SOAP Generation**: Automatically generate structured SOAP notes from transcripts
- **Dynamic Checklist**: Ensure completeness with AI-evaluated documentation checklists
- **Hybrid Search**: Powerful search combining full-text and semantic search
- **External Integrations**: Connect with Helssa for patient data and send SMS notifications
- **Analytics Dashboard**: Monitor system performance and usage metrics
- **React Frontend**: Modern, responsive web interface for easy interaction

## 📁 Project Structure

```
soapify/
├── accounts/           # User authentication and management
├── encounters/         # Patient encounter management
├── stt/               # Speech-to-text processing
├── nlp/               # Natural language processing & SOAP generation
├── outputs/           # Report generation (PDF, Markdown)
├── integrations/      # External service integrations
├── checklist/         # Dynamic checklist evaluation
├── embeddings/        # Vector embeddings for semantic search
├── search/            # Hybrid search functionality
├── analytics/         # System analytics and monitoring
├── adminplus/         # Advanced admin dashboard
├── worker/            # Celery task management
├── infra/             # Infrastructure utilities
├── front/             # React frontend application
└── soapify/           # Main Django project settings
```

## 🚀 Quick Start (Home Environment)

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for backend development)
- Node.js 16+ (for frontend development)
- OpenAI API key (or GapGPT key)

### Setup for Home Use

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd soapify
   ```

2. **Copy environment files**
   ```bash
   cp .env.home.example .env.home
   # Edit .env.home with your API keys
   ```

3. **Initial setup**
   ```bash
   make -f Makefile.home setup
   ```

4. **Start all services**
   ```bash
   make -f Makefile.home start
   ```

5. **Start with frontend**
   ```bash
   make -f Makefile.home frontend
   ```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/swagger
- **Flower (Celery)**: http://localhost:5555
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## 💻 Frontend Development

The React frontend provides a complete interface for interacting with SOAPify:

### Features
- User authentication with JWT
- Dashboard with real-time statistics
- Encounter management
- Audio file upload with drag-and-drop
- Real-time transcription status
- SOAP note editing
- Advanced search functionality
- Analytics visualization

### Development
```bash
cd front
npm install
npm start
```

### Build
```bash
npm run build
```

## 🔧 Backend Development

### Running without Docker
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Running tests
```bash
python manage.py test
```

## 🐳 Docker Commands

### Using docker-compose.home.yml (Optimized for home computers)

```bash
# Start services
docker-compose -f docker-compose.home.yml up -d

# View logs
docker-compose -f docker-compose.home.yml logs -f

# Stop services
docker-compose -f docker-compose.home.yml down

# Clean everything
docker-compose -f docker-compose.home.yml down -v
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/token/` - Get JWT tokens
- `POST /api/auth/token/refresh/` - Refresh access token
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout

### Core Functionality
- `/api/encounters/` - Manage patient encounters
- `/api/stt/` - Speech-to-text operations
- `/api/nlp/` - SOAP note generation
- `/api/search/` - Search functionality
- `/api/analytics/` - System analytics
- `/api/outputs/` - Report generation

Full API documentation available at `/swagger` when running the server.

## 🔒 Security Features

- JWT authentication with token refresh
- HMAC authentication for sensitive endpoints
- Rate limiting on API endpoints
- CORS configuration
- SQL injection protection
- XSS protection
- CSRF protection

## 🚀 Production Deployment

For production deployment, use the main docker-compose files:

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Or use the deployment script
./scripts/deploy.sh production your-domain.com
```

Refer to `DEPLOYMENT_GUIDE.md` for detailed production setup instructions.

## 📊 System Requirements

### Minimum (Home/Development)
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB

### Recommended (Production)
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ (depends on audio storage needs)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For issues and questions:
- Check the documentation in `/docs`
- Review API documentation at `/swagger`
- Contact the development team

## 🎯 Roadmap

- [ ] Mobile application
- [ ] Real-time collaboration
- [ ] Multi-language support
- [ ] Voice commands
- [ ] Advanced analytics
- [ ] Plugin system

---

Built with ❤️ by the SOAPify Team