#!/bin/bash

# SOAPify Restore Script
set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la /backups/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE=$1
POSTGRES_USER=${POSTGRES_USER:-soapify}
POSTGRES_DB=${POSTGRES_DB:-soapify}
POSTGRES_HOST=${POSTGRES_HOST:-db}

echo "🔄 Starting restore process..."
echo "📁 Backup file: $BACKUP_FILE"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Confirm restore
echo "⚠️  This will replace the current database with the backup."
echo "📋 Database: $POSTGRES_DB on $POSTGRES_HOST"
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Restore cancelled"
    exit 1
fi

# Stop services that might be using the database
echo "🛑 Stopping services..."
docker-compose stop web celery-worker celery-beat || true

# Drop existing database and recreate
echo "🗄️ Preparing database..."
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}_restore;"
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "CREATE DATABASE ${POSTGRES_DB}_restore;"

# Restore from backup
echo "📥 Restoring database..."
if [[ $BACKUP_FILE == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql -h $POSTGRES_HOST -U $POSTGRES_USER -d ${POSTGRES_DB}_restore
else
    psql -h $POSTGRES_HOST -U $POSTGRES_USER -d ${POSTGRES_DB}_restore < "$BACKUP_FILE"
fi

# Switch databases
echo "🔄 Switching to restored database..."
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}_old;"
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "ALTER DATABASE $POSTGRES_DB RENAME TO ${POSTGRES_DB}_old;"
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "ALTER DATABASE ${POSTGRES_DB}_restore RENAME TO $POSTGRES_DB;"

# Start services
echo "▶️ Starting services..."
docker-compose start web celery-worker celery-beat

# Run migrations to ensure schema is up to date
echo "🔧 Running migrations..."
docker-compose exec web python manage.py migrate

echo "✅ Restore completed successfully!"
echo "🗑️ Old database is kept as ${POSTGRES_DB}_old"
echo "   You can drop it manually if the restore is working correctly:"
echo "   psql -h $POSTGRES_HOST -U $POSTGRES_USER -c \"DROP DATABASE ${POSTGRES_DB}_old;\""