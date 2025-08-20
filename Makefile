# SOAPify Makefile

.PHONY: help dev prod test clean deploy backup restore health

# Default environment
ENV ?= development
DOMAIN ?= localhost

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)SOAPify Development Commands$(NC)"
	@echo "=============================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development Commands
dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Development environment started$(NC)"
	@echo "🌐 Application: http://localhost:8000"
	@echo "👤 Admin: http://localhost:8000/admin/"
	@echo "📊 AdminPlus: http://localhost:8000/adminplus/"
	@echo "🌸 Flower: http://localhost:5555"

dev-build: ## Build and start development environment
	@echo "$(BLUE)Building and starting development environment...$(NC)"
	docker-compose build
	docker-compose up -d

dev-logs: ## Show development logs
	docker-compose logs -f

dev-shell: ## Open Django shell in development
	docker-compose exec web python manage.py shell

dev-dbshell: ## Open database shell in development
	docker-compose exec web python manage.py dbshell

# Production Commands
prod: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✅ Production environment started$(NC)"

prod-build: ## Build and start production environment
	@echo "$(BLUE)Building and starting production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml build
	docker-compose -f docker-compose.prod.yml up -d

prod-logs: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

# Database Commands
migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	docker-compose exec web python manage.py migrate
	@echo "$(GREEN)✅ Migrations completed$(NC)"

makemigrations: ## Create new database migrations
	@echo "$(BLUE)Creating database migrations...$(NC)"
	docker-compose exec web python manage.py makemigrations
	@echo "$(GREEN)✅ Migrations created$(NC)"

superuser: ## Create Django superuser
	@echo "$(BLUE)Creating superuser...$(NC)"
	docker-compose exec web python manage.py createsuperuser

loaddata: ## Load initial data
	@echo "$(BLUE)Loading initial data...$(NC)"
	docker-compose exec web python manage.py loaddata fixtures/initial_data.json || echo "No fixtures found"

# Testing Commands
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	docker-compose exec web python manage.py test
	@echo "$(GREEN)✅ Tests completed$(NC)"

test-coverage: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose exec web coverage run --source='.' manage.py test
	docker-compose exec web coverage report
	docker-compose exec web coverage html
	@echo "$(GREEN)✅ Coverage report generated$(NC)"

test-specific: ## Run specific test (usage: make test-specific TEST=app.tests.TestClass)
	@echo "$(BLUE)Running specific test: $(TEST)$(NC)"
	docker-compose exec web python manage.py test $(TEST)

# Deployment Commands
deploy: ## Deploy to production
	@echo "$(BLUE)Deploying to $(ENV) environment...$(NC)"
	./scripts/deploy.sh $(ENV) $(DOMAIN)
	@echo "$(GREEN)✅ Deployment completed$(NC)"

backup: ## Create database backup
	@echo "$(BLUE)Creating backup...$(NC)"
	./scripts/backup.sh
	@echo "$(GREEN)✅ Backup completed$(NC)"

restore: ## Restore from backup (usage: make restore BACKUP_FILE=/path/to/backup.sql.gz)
	@echo "$(BLUE)Restoring from backup...$(NC)"
	./scripts/restore.sh $(BACKUP_FILE)
	@echo "$(GREEN)✅ Restore completed$(NC)"

health: ## Run health check
	@echo "$(BLUE)Running health check...$(NC)"
	./scripts/health_check.sh $(ENV)

# Maintenance Commands
clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-all: ## Clean up all Docker resources including images
	@echo "$(YELLOW)⚠️  This will remove all Docker images and containers$(NC)"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker system prune -af; \
		echo "$(GREEN)✅ Complete cleanup finished$(NC)"; \
	else \
		echo "$(RED)❌ Cleanup cancelled$(NC)"; \
	fi

restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✅ Services restarted$(NC)"

restart-web: ## Restart web service only
	@echo "$(BLUE)Restarting web service...$(NC)"
	docker-compose restart web
	@echo "$(GREEN)✅ Web service restarted$(NC)"

restart-workers: ## Restart Celery workers
	@echo "$(BLUE)Restarting Celery workers...$(NC)"
	docker-compose restart celery-worker celery-beat
	@echo "$(GREEN)✅ Workers restarted$(NC)"

# Development Utilities
collectstatic: ## Collect static files
	@echo "$(BLUE)Collecting static files...$(NC)"
	docker-compose exec web python manage.py collectstatic --noinput
	@echo "$(GREEN)✅ Static files collected$(NC)"

check: ## Run Django system checks
	@echo "$(BLUE)Running Django system checks...$(NC)"
	docker-compose exec web python manage.py check
	@echo "$(GREEN)✅ System checks passed$(NC)"

lint: ## Run code linting
	@echo "$(BLUE)Running code linting...$(NC)"
	docker-compose exec web flake8 . || echo "Flake8 not installed"
	docker-compose exec web black --check . || echo "Black not installed"
	@echo "$(GREEN)✅ Linting completed$(NC)"

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	docker-compose exec web black . || echo "Black not installed"
	docker-compose exec web isort . || echo "isort not installed"
	@echo "$(GREEN)✅ Code formatted$(NC)"

# Monitoring Commands
logs-web: ## Show web service logs
	docker-compose logs -f web

logs-celery: ## Show Celery logs
	docker-compose logs -f celery-worker celery-beat

logs-db: ## Show database logs
	docker-compose logs -f db

logs-redis: ## Show Redis logs
	docker-compose logs -f redis

stats: ## Show Docker container stats
	docker stats

ps: ## Show running containers
	docker-compose ps

# Database Utilities
db-reset: ## Reset database (WARNING: This will delete all data)
	@echo "$(RED)⚠️  WARNING: This will delete all database data!$(NC)"
	@read -p "Are you sure you want to reset the database? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker-compose up -d db redis; \
		sleep 5; \
		docker-compose up -d web; \
		sleep 10; \
		docker-compose exec web python manage.py migrate; \
		docker-compose exec web python manage.py createsuperuser --noinput --username admin --email admin@soapify.com || true; \
		echo "$(GREEN)✅ Database reset completed$(NC)"; \
	else \
		echo "$(RED)❌ Database reset cancelled$(NC)"; \
	fi

db-dump: ## Create database dump
	@echo "$(BLUE)Creating database dump...$(NC)"
	docker-compose exec db pg_dump -U soapify soapify > dump_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database dump created$(NC)"

db-restore-dump: ## Restore database from dump (usage: make db-restore-dump DUMP_FILE=dump.sql)
	@echo "$(BLUE)Restoring database from dump...$(NC)"
	docker-compose exec -T db psql -U soapify soapify < $(DUMP_FILE)
	@echo "$(GREEN)✅ Database restored from dump$(NC)"

# Setup Commands
setup: ## Initial project setup
	@echo "$(BLUE)Setting up SOAPify project...$(NC)"
	cp .env.example .env || echo ".env already exists"
	docker-compose build
	docker-compose up -d
	sleep 10
	docker-compose exec web python manage.py migrate
	@echo "$(GREEN)✅ Project setup completed$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "1. Edit .env file with your configuration"
	@echo "2. Run 'make superuser' to create an admin user"
	@echo "3. Visit http://localhost:8000/admin/ to access the admin interface"

setup-prod: ## Initial production setup
	@echo "$(BLUE)Setting up production environment...$(NC)"
	cp .env.example .env.prod || echo ".env.prod already exists"
	@echo "$(YELLOW)Please edit .env.prod with your production configuration$(NC)"
	@echo "$(YELLOW)Then run: make deploy ENV=production DOMAIN=your-domain.com$(NC)"

# SSL Commands
ssl-generate: ## Generate self-signed SSL certificate for development
	@echo "$(BLUE)Generating self-signed SSL certificate...$(NC)"
	mkdir -p ssl
	openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
	@echo "$(GREEN)✅ SSL certificate generated$(NC)"

ssl-letsencrypt: ## Generate Let's Encrypt SSL certificate (usage: make ssl-letsencrypt DOMAIN=your-domain.com)
	@echo "$(BLUE)Generating Let's Encrypt SSL certificate for $(DOMAIN)...$(NC)"
	sudo certbot certonly --standalone -d $(DOMAIN)
	sudo cp /etc/letsencrypt/live/$(DOMAIN)/fullchain.pem ssl/cert.pem
	sudo cp /etc/letsencrypt/live/$(DOMAIN)/privkey.pem ssl/key.pem
	sudo chown $$USER:$$USER ssl/*.pem
	@echo "$(GREEN)✅ Let's Encrypt certificate installed$(NC)"

# Quick Commands
up: dev ## Alias for dev command
down: ## Stop all services
	docker-compose down

build: dev-build ## Alias for dev-build command

shell: dev-shell ## Alias for dev-shell command

# Help for specific environments
help-dev: ## Show development-specific help
	@echo "$(BLUE)Development Commands:$(NC)"
	@echo "make dev          - Start development environment"
	@echo "make dev-build    - Build and start development"
	@echo "make shell        - Open Django shell"
	@echo "make test         - Run tests"
	@echo "make migrate      - Run migrations"
	@echo "make superuser    - Create superuser"

help-prod: ## Show production-specific help
	@echo "$(BLUE)Production Commands:$(NC)"
	@echo "make deploy       - Deploy to production"
	@echo "make backup       - Create backup"
	@echo "make health       - Run health check"
	@echo "make prod-logs    - Show production logs"