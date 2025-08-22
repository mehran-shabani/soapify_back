# Docker Setup for Soapify Django Application

This Docker setup includes Django, MySQL, Redis, Celery, and Nginx configured for production use.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your configurations:**
   - Update database passwords
   - Set your SECRET_KEY
   - Configure external services (OpenAI, S3, etc.)

3. **Build and start services:**
   ```bash
   make build
   make up
   ```

4. **Run migrations:**
   ```bash
   make migrate
   ```

5. **Create superuser (optional):**
   ```bash
   make createsuperuser
   ```

## Services

- **web**: Django application (Gunicorn)
- **db**: MySQL 8.0 database
- **redis**: Redis for caching and Celery broker
- **celery_worker**: Background task processing
- **celery_beat**: Scheduled tasks
- **flower**: Celery monitoring (port 5555)
- **nginx**: Web server and reverse proxy

## Common Commands

```bash
# View all available commands
make help

# Start services
make up

# Stop services
make down

# View logs
make logs

# Django shell
make shell

# Run tests
make test

# Database backup
make backup-db
```

## Accessing Services

- **Django Application**: http://localhost:8000 (through Nginx)
- **Flower (Celery Monitor)**: http://localhost:5555
- **MySQL**: localhost:3306 (only from host machine)
- **Redis**: localhost:6379 (only from host machine)

## Production Deployment

1. **SSL Certificates**: 
   - Add your SSL certificates to `nginx/ssl/`
   - Uncomment SSL configuration in `nginx/conf.d/soapify.conf`

2. **Environment Variables**:
   - Set `DEBUG=False`
   - Use strong passwords
   - Configure proper ALLOWED_HOSTS

3. **Security**:
   - Change all default passwords
   - Enable security headers in nginx
   - Configure firewall rules

## Troubleshooting

1. **Database connection issues:**
   ```bash
   docker-compose logs db
   ```

2. **Permission issues:**
   ```bash
   docker-compose exec web ls -la /app
   ```

3. **Rebuild after requirements change:**
   ```bash
   docker-compose build --no-cache web
   ```

## Directory Structure

```
.
├── docker-compose.yml      # Main Docker Compose configuration
├── Dockerfile             # Django application Docker image
├── entrypoint.sh         # Container initialization script
├── .env                  # Environment variables (create from .env.example)
├── .dockerignore         # Files to exclude from Docker build
├── Makefile              # Convenience commands
├── nginx/                # Nginx configuration
│   ├── nginx.conf        # Main Nginx config
│   └── conf.d/           # Site-specific configs
│       └── soapify.conf  # Django app config
└── requirements.txt      # Python dependencies
```

## Testing API

The application is deployed at https://django-m.chbk.app for testing.