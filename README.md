# SOAPify - AI-Powered Medical Documentation System

SOAPify is a comprehensive Django-based platform that transforms patient encounter audio recordings into structured SOAP (Subjective, Objective, Assessment, Plan) notes using advanced AI technologies.

## 🌟 Features

### Core Functionality
- **Audio Processing**: Upload and transcribe medical encounter audio files
- **AI-Powered SOAP Generation**: Automatic generation of structured medical notes
- **Checklist Evaluation**: Intelligent assessment of documentation completeness
- **Multi-format Export**: Generate reports in Markdown, PDF formats
- **SMS Integration**: Send reports via SMS to patients/providers

### Advanced Features
- **Semantic Search**: Find relevant information across all encounters
- **Embedding-based Analysis**: Vector similarity search for related content
- **Real-time Analytics**: Performance monitoring and business metrics
- **Admin Dashboard**: Comprehensive system monitoring and management
- **Task Management**: Asynchronous processing with Celery
- **Multi-tenant Support**: Role-based access control

### Integrations
- **GapGPT**: AI processing for transcription and text generation
- **Helssa**: Patient data integration
- **Crazy Miner**: SMS and OTP services
- **S3 Storage**: Secure file storage and management

## 🏗️ Architecture

SOAPify follows a modular architecture with the following components:

### Core Applications
- **accounts**: User authentication and authorization
- **encounters**: Patient encounter management
- **stt**: Speech-to-text processing
- **nlp**: Natural language processing and SOAP generation
- **outputs**: Report generation and export
- **integrations**: External service integrations

### Supporting Modules
- **checklist**: Documentation completeness evaluation
- **embeddings**: Vector embeddings for semantic search
- **search**: Hybrid search functionality
- **analytics**: System monitoring and metrics
- **adminplus**: Advanced administrative tools
- **infra**: Infrastructure utilities and middleware
- **worker**: Celery task management

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+ (for production)
- Redis 7+ (for caching and task queue)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd soapify
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development environment**
   ```bash
   docker-compose up -d
   ```

4. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - Main application: http://localhost:8000
   - Admin interface: http://localhost:8000/admin/
   - Admin Plus: http://localhost:8000/adminplus/
   - Flower (Celery monitoring): http://localhost:5555

### Production Deployment

1. **Prepare production environment**
   ```bash
   cp .env.example .env.prod
   # Configure production settings in .env.prod
   ```

2. **Deploy using the deployment script**
   ```bash
   ./scripts/deploy.sh production your-domain.com
   ```

3. **Set up SSL certificates**
   ```bash
   # Place your SSL certificates in the ssl/ directory
   # cert.pem and key.pem
   ```

4. **Configure monitoring and backups**
   ```bash
   # Set up automated backups
   crontab -e
   # Add: 0 2 * * * /path/to/soapify/scripts/backup.sh
   ```

## 📚 API Documentation

### Authentication

SOAPify uses JWT (JSON Web Tokens) for authentication.

#### Obtain Token
```http
POST /api/auth/token/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

#### Refresh Token
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token"
}
```

### Core Endpoints

#### Encounters

**Create Encounter**
```http
POST /api/encounters/
Authorization: Bearer <token>
Content-Type: application/json

{
    "patient_name": "John Doe",
    "patient_id": "P12345",
    "encounter_type": "consultation"
}
```

**Upload Audio Chunk**
```http
POST /api/encounters/{id}/chunks/presign
Authorization: Bearer <token>
Content-Type: application/json

{
    "filename": "audio_chunk_1.wav",
    "content_type": "audio/wav"
}
```

**Commit Audio Chunk**
```http
POST /api/encounters/{id}/chunks/commit
Authorization: Bearer <token>
Content-Type: application/json

{
    "s3_key": "uploads/audio_chunk_1.wav",
    "etag": "abc123def456",
    "sha256_hash": "hash_value",
    "idempotency_key": "unique_key"
}
```

#### SOAP Generation

**Generate SOAP Draft**
```http
POST /api/nlp/soap/draft
Authorization: Bearer <token>
Content-Type: application/json

{
    "encounter_id": 123
}
```

**Finalize SOAP Note**
```http
POST /api/nlp/soap/finalize
Authorization: Bearer <token>
Content-Type: application/json

{
    "encounter_id": 123,
    "idempotency_key": "unique_key"
}
```

#### Checklist Evaluation

**Evaluate Encounter**
```http
POST /api/checklist/evaluations/evaluate_encounter/
Authorization: Bearer <token>
Content-Type: application/json

{
    "encounter_id": 123,
    "template_id": 1
}
```

**Get Checklist Summary**
```http
GET /api/checklist/evaluations/summary/?encounter_id=123
Authorization: Bearer <token>
```

#### Search

**Search Content**
```http
GET /api/search/?q=patient+symptoms&content_type=transcript&page=1
Authorization: Bearer <token>
```

**Search Suggestions**
```http
GET /api/search/suggestions/?q=headache
Authorization: Bearer <token>
```

#### Analytics

**System Overview**
```http
GET /api/analytics/overview/
Authorization: Bearer <token>
```

**User Analytics**
```http
GET /api/analytics/users/?days=30
Authorization: Bearer <token>
```

#### Outputs

**Generate Final Report**
```http
POST /api/outputs/finalize
Authorization: Bearer <token>
Content-Type: application/json

{
    "encounter_id": 123,
    "export_formats": ["pdf", "markdown"],
    "send_sms": true,
    "recipient_phone": "+1234567890"
}
```

## 🔧 Configuration

### Environment Variables

#### Django Settings
- `SECRET_KEY`: Django secret key (required)
- `DEBUG`: Debug mode (default: False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

#### Database
- `DATABASE_URL`: PostgreSQL connection string
- For development, SQLite is used by default

#### Redis/Celery
- `REDIS_URL`: Redis connection string (default: redis://localhost:6379/0)

#### S3 Storage
- `S3_ACCESS_KEY_ID`: AWS S3 access key
- `S3_SECRET_ACCESS_KEY`: AWS S3 secret key
- `S3_BUCKET_NAME`: S3 bucket name
- `S3_REGION_NAME`: S3 region (default: us-east-1)
- `S3_ENDPOINT_URL`: S3 endpoint URL

#### AI Services
- `OPENAI_API_KEY`: OpenAI/GapGPT API key
- `OPENAI_BASE_URL`: API base URL (default: https://api.gapgpt.app/v1)

#### Security
- `HMAC_SHARED_SECRET`: Shared secret for HMAC authentication
- `LOCAL_JWT_SECRET`: JWT signing key

#### External Integrations
- `HELSSA_API_KEY`: Helssa integration API key
- `HELSSA_SHARED_SECRET`: Helssa shared secret
- `CRAZY_MINER_API_KEY`: Crazy Miner SMS API key
- `CRAZY_MINER_SHARED_SECRET`: Crazy Miner shared secret

## 🧪 Testing

### Run Tests
```bash
# Run all tests
docker-compose exec web python manage.py test

# Run specific app tests
docker-compose exec web python manage.py test encounters

# Run with coverage
docker-compose exec web coverage run --source='.' manage.py test
docker-compose exec web coverage report
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Service integration testing
- **API Tests**: Endpoint functionality testing
- **Performance Tests**: Load and performance testing

## 📊 Monitoring

### Health Checks
```bash
# Run health check script
./scripts/health_check.sh production
```

### Monitoring Endpoints
- System health: `/admin/health/`
- Celery monitoring: http://localhost:5555 (Flower)
- Admin Plus dashboard: `/adminplus/`

### Metrics and Analytics
- Real-time performance metrics
- Business analytics dashboard
- Alert system for critical issues
- Automated reporting

## 🔒 Security

### Security Features
- JWT-based authentication
- HMAC signature verification for sensitive endpoints
- Rate limiting on API endpoints
- CORS protection
- SQL injection prevention
- XSS protection
- CSRF protection

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
- Referrer-Policy

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database status
docker-compose exec db pg_isready -U soapify

# View database logs
docker-compose logs db
```

#### Celery Worker Issues
```bash
# Check worker status
docker-compose exec web celery -A soapify inspect active

# Restart workers
docker-compose restart celery-worker
```

#### File Upload Issues
```bash
# Check S3 configuration
docker-compose exec web python manage.py check_s3_connection

# View upload logs
docker-compose logs web | grep upload
```

### Log Locations
- Application logs: `/app/logs/`
- Nginx logs: `/var/log/nginx/`
- Database logs: Docker container logs
- Celery logs: Docker container logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- OpenAI for AI capabilities
- Celery for task processing
- PostgreSQL and Redis teams
- All contributors and testers

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation and troubleshooting guide

---


