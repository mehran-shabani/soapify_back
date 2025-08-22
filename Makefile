.PHONY: help build up down restart logs shell migrate makemigrations test clean

help:
	@echo "Available commands:"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo "  make logs         - View logs from all services"
	@echo "  make shell        - Open Django shell"
	@echo "  make migrate      - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Remove volumes and containers"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec web python manage.py shell

migrate:
	docker-compose exec web python manage.py migrate

makemigrations:
	docker-compose exec web python manage.py makemigrations

test:
	docker-compose exec web python manage.py test

clean:
	docker-compose down -v
	docker system prune -f

# Production commands
prod-up:
	docker-compose -f docker-compose.yml up -d

prod-down:
	docker-compose -f docker-compose.yml down

prod-logs:
	docker-compose -f docker-compose.yml logs -f

# Database backup
backup-db:
	docker-compose exec db mysqldump -u root -p$$DB_ROOT_PASSWORD $$DB_DATABASE > backup_$$(date +%Y%m%d_%H%M%S).sql

# Create superuser
createsuperuser:
	docker-compose exec web python manage.py createsuperuser