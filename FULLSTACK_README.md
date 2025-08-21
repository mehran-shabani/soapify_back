# SOAPify Full Stack Application

This document provides comprehensive instructions for running the complete SOAPify application with both backend (Django) and frontend (React).

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git
- 8GB+ RAM recommended
- Port 80, 3000, 8000, 5432, 6379 available

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd soapify

# Copy environment file
cp .env.example .env

# Edit .env file with your settings (optional)
nano .env
```

### 2. Start the Application

```bash
# Build and start all services
make -f Makefile.fullstack build
make -f Makefile.fullstack up

# Or with development frontend (hot reload)
make -f Makefile.fullstack up-dev
```

### 3. Access the Application

- **Frontend**: http://localhost
- **Frontend Dev**: http://localhost:3000 (if using up-dev)
- **Backend API**: http://localhost:8000/api
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/api/docs

### 4. Create Admin User

```bash
make -f Makefile.fullstack superuser
```

Use username: `admin` and a secure password.

## 📁 Project Structure

```
soapify/
├── front/                 # React frontend application
│   ├── src/              # Source code
│   │   ├── components/   # Reusable components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   ├── store/        # Redux store
│   │   └── theme/        # MUI theme
│   ├── public/           # Static assets
│   ├── Dockerfile        # Production build
│   └── Dockerfile.dev    # Development build
├── soapify/              # Django backend
├── accounts/             # User management
├── encounters/           # Medical encounters
├── apis/                 # API endpoints
├── crazy_miner/          # CrazyMiner integration
├── docker-compose.fullstack.yml
├── .env                  # Environment variables
└── Makefile.fullstack    # Helper commands
```

## 🛠️ Available Commands

### Docker Management

```bash
# Start services
make -f Makefile.fullstack up          # Production mode
make -f Makefile.fullstack up-dev      # Development mode
make -f Makefile.fullstack up-prod     # With Nginx proxy

# Stop services
make -f Makefile.fullstack down

# View logs
make -f Makefile.fullstack logs
make -f Makefile.fullstack logs-web      # Backend logs
make -f Makefile.fullstack logs-frontend # Frontend logs

# Shell access
make -f Makefile.fullstack shell-web      # Backend shell
make -f Makefile.fullstack shell-frontend # Frontend shell
make -f Makefile.fullstack shell-db       # Database shell
```

### Database Management

```bash
# Run migrations
make -f Makefile.fullstack migrate

# Create migrations
make -f Makefile.fullstack makemigrations

# Backup database
make -f Makefile.fullstack db-backup

# Restore database
make -f Makefile.fullstack db-restore FILE=backup.sql
```

### Development

```bash
# Run tests
make -f Makefile.fullstack test          # Backend tests
make -f Makefile.fullstack test-frontend # Frontend tests

# Frontend development
cd front
npm install                              # Install dependencies
npm start                                # Start dev server
npm run build                            # Build for production
npm run lint                             # Run linter
```

## 🧪 Testing the API

The React application includes a comprehensive API Tester at http://localhost/api-tester

### Features:
- Interactive API endpoint testing
- Pre-configured common endpoints
- Request/response visualization
- File upload support
- Authentication handling

### Test Workflow:

1. **Login**: 
   - Go to http://localhost/login
   - Use credentials: admin / [your-password]

2. **Test Endpoints**:
   - Navigate to API Tester
   - Select method and endpoint
   - Add headers/body as needed
   - Send request and view response

3. **Common Test Scenarios**:
   - Create patient
   - Upload audio file
   - Process encounter
   - Generate SOAP note
   - View analytics

## 🔧 Environment Variables

Key environment variables in `.env`:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=soapify
DB_USER=soapify
DB_PASSWORD=soapify_password

# Frontend
FRONTEND_URL=http://localhost:3000

# API Keys (optional)
OPENAI_API_KEY=your-key-here

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:80
```

## 🐛 Troubleshooting

### Common Issues:

1. **Port conflicts**:
   ```bash
   # Check what's using ports
   lsof -i :80
   lsof -i :8000
   lsof -i :3000
   ```

2. **Database connection issues**:
   ```bash
   # Check database is running
   docker-compose -f docker-compose.fullstack.yml ps db
   
   # Check logs
   docker-compose -f docker-compose.fullstack.yml logs db
   ```

3. **Frontend not connecting to backend**:
   - Check CORS settings in .env
   - Verify REACT_APP_API_URL is correct
   - Check backend is running: http://localhost:8000/api

4. **Clean restart**:
   ```bash
   make -f Makefile.fullstack clean
   make -f Makefile.fullstack build
   make -f Makefile.fullstack up
   ```

## 🚀 Production Deployment

For production deployment:

1. Update `.env` with production values
2. Set `DEBUG=False`
3. Use strong `SECRET_KEY`
4. Configure proper database credentials
5. Set up SSL/TLS certificates
6. Use production-grade web server (Nginx)

```bash
# Production-like setup locally
make -f Makefile.fullstack up-prod
# Access via: http://localhost:8080
```

## 📚 API Documentation

### Authentication
All API endpoints (except login) require JWT authentication:

```javascript
headers: {
  'Authorization': 'Bearer <access_token>'
}
```

### Key Endpoints:

- `POST /api/auth/token/` - Get JWT tokens
- `POST /api/auth/token/refresh/` - Refresh token
- `GET /api/encounters/` - List encounters
- `POST /api/encounters/` - Create encounter with audio
- `GET /api/patients/` - List patients
- `POST /api/patients/` - Create patient
- `GET /api/analytics/dashboard/` - Get analytics

## 🏗️ Architecture

### Backend (Django)
- REST API with Django REST Framework
- PostgreSQL database
- Redis for caching and Celery
- Celery for async tasks
- JWT authentication

### Frontend (React)
- React 18 with TypeScript
- Material-UI for components
- Redux Toolkit for state management
- React Router for navigation
- Axios for API calls

### Infrastructure
- Docker containerization
- Nginx reverse proxy
- PostgreSQL 16
- Redis 7
- Celery workers

## 📞 Support

For issues or questions:
1. Check logs: `make -f Makefile.fullstack logs`
2. Review this documentation
3. Check `.env` configuration
4. Ensure all services are running

## 🔒 Security Notes

- Change default passwords in production
- Use HTTPS in production
- Keep SECRET_KEY secure
- Regular security updates
- Implement rate limiting
- Use environment-specific settings

---

Happy testing! 🎉