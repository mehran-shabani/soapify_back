#!/bin/bash

# SOAPify Backup Script
set -e

echo "💾 Starting backup process..."

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
POSTGRES_USER=${POSTGRES_USER:-soapify}
POSTGRES_DB=${POSTGRES_DB:-soapify}
POSTGRES_HOST=${POSTGRES_HOST:-db}

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Database backup
echo "🗄️ Backing up PostgreSQL database..."
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB --no-password > "$BACKUP_DIR/db_backup_$DATE.sql"

# Compress the backup
echo "🗜️ Compressing database backup..."
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# Redis backup (if needed)
if [ "$BACKUP_REDIS" = "true" ]; then
    echo "📊 Backing up Redis data..."
    redis-cli --rdb "$BACKUP_DIR/redis_backup_$DATE.rdb" || echo "Redis backup failed or not needed"
fi

# Media files backup (if configured)
if [ -d "/app/media" ] && [ "$BACKUP_MEDIA" = "true" ]; then
    echo "📁 Backing up media files..."
    tar -czf "$BACKUP_DIR/media_backup_$DATE.tar.gz" -C /app media/
fi

# Clean up old backups (keep last 7 days)
echo "🧹 Cleaning up old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "✅ Backup completed successfully!"
echo "📁 Backup files saved in: $BACKUP_DIR"
ls -la $BACKUP_DIR/*$DATE*