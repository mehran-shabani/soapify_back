# SOAPify Deployment Guide

این راهنما شامل دستورالعمل‌های کامل برای دیپلوی SOAPify در محیط production است.

## 🚀 دیپلوی سریع (Quick Deploy)

### پیش‌نیازها

```bash
# نصب Docker و Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# نصب Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### مراحل دیپلوی

#### 1. کلون پروژه

```bash
git clone <repository-url>
cd soapify
```

#### 2. تنظیم متغیرهای محیطی

```bash
cp .env.example .env.prod
nano .env.prod
```

**متغیرهای ضروری:**

```env
# Django
SECRET_KEY=your-super-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
DATABASE_URL=postgresql://soapify:secure_password@db:5432/soapify
POSTGRES_DB=soapify
POSTGRES_USER=soapify
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://redis:6379/0

# S3 Storage
S3_ACCESS_KEY_ID=your_s3_access_key
S3_SECRET_ACCESS_KEY=your_s3_secret_key
S3_BUCKET_NAME=soapify-prod
S3_REGION_NAME=us-east-1

# AI Services
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.gapgpt.app/v1

# Security
HMAC_SHARED_SECRET=your-hmac-secret
LOCAL_JWT_SECRET=your-jwt-secret

# External Services
HELSSA_API_KEY=your_helssa_key
CRAZY_MINER_API_KEY=your_sms_key
```

#### 3. تنظیم SSL

```bash
# ایجاد دایرکتوری SSL
mkdir -p ssl

# کپی کردن گواهی‌نامه‌ها
cp your_certificate.pem ssl/cert.pem
cp your_private_key.pem ssl/key.pem

# یا استفاده از Let's Encrypt
sudo apt install certbot
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

#### 4. اجرای دیپلوی

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh production your-domain.com
```

#### 5. تست سیستم

```bash
./scripts/health_check.sh production
```

## 🔧 تنظیمات پیشرفته

### تنظیم پایگاه داده خارجی

اگر از PostgreSQL خارجی استفاده می‌کنید:

```bash
# ایجاد پایگاه داده
createdb -h your-db-host -U postgres soapify

# تنظیم متغیر محیطی
DATABASE_URL=postgresql://user:pass@your-db-host:5432/soapify
```

### تنظیم Redis خارجی

```bash
# تنظیم Redis خارجی
REDIS_URL=redis://your-redis-host:6379/0

# یا Redis با authentication
REDIS_URL=redis://username:password@your-redis-host:6379/0
```

### تنظیم Load Balancer

برای ترافیک بالا، از چندین instance استفاده کنید:

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  web:
    deploy:
      replicas: 3
  
  nginx:
    depends_on:
      - web
    environment:
      - UPSTREAM_SERVERS=web:8000
```

```bash
docker-compose -f docker-compose.prod.yml -f docker-compose.scale.yml up -d --scale web=3
```

## 📊 مانیتورینگ و لاگ‌ها

### تنظیم Monitoring

#### 1. Prometheus و Grafana

```bash
# اضافه کردن به docker-compose
git clone https://github.com/your-org/soapify-monitoring
docker-compose -f docker-compose.prod.yml -f monitoring/docker-compose.monitoring.yml up -d
```

#### 2. ELK Stack برای لاگ‌ها

```yaml
# در docker-compose.prod.yml
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    depends_on:
      - elasticsearch
```

### مشاهده لاگ‌ها

```bash
# لاگ‌های کلی
docker-compose -f docker-compose.prod.yml logs -f

# لاگ‌های سرویس خاص
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# لاگ‌های Nginx
tail -f logs/nginx/access.log
tail -f logs/nginx/error.log
```

## 🔐 امنیت

### تنظیمات Firewall

```bash
# اجازه دسترسی فقط به پورت‌های ضروری
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### تنظیم SSL/TLS

```nginx
# در nginx.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
```

### Backup خودکار

```bash
# اضافه کردن به crontab
crontab -e

# پشتیبان‌گیری روزانه
0 2 * * * /path/to/soapify/scripts/backup.sh

# پاک‌سازی لاگ‌های قدیمی
0 3 * * 0 find /path/to/logs -name "*.log" -mtime +30 -delete
```

## 🚨 عیب‌یابی

### مشکلات رایج

#### 1. خطای اتصال به پایگاه داده

```bash
# بررسی وضعیت پایگاه داده
docker-compose -f docker-compose.prod.yml exec db pg_isready -U soapify

# بررسی لاگ‌های پایگاه داده
docker-compose -f docker-compose.prod.yml logs db

# تست اتصال از Django
docker-compose -f docker-compose.prod.yml exec web python manage.py dbshell
```

#### 2. مشکل Celery Workers

```bash
# بررسی وضعیت workerها
docker-compose -f docker-compose.prod.yml exec web celery -A soapify inspect active

# ری‌استارت worker ها
docker-compose -f docker-compose.prod.yml restart celery-worker-default

# مشاهده صف‌های Celery
docker-compose -f docker-compose.prod.yml exec web celery -A soapify inspect reserved
```

#### 3. مشکل آپلود فایل

```bash
# بررسی تنظیمات S3
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
>>> from django.conf import settings
>>> print(settings.AWS_ACCESS_KEY_ID)
>>> print(settings.S3_BUCKET_NAME)

# تست اتصال S3
docker-compose -f docker-compose.prod.yml exec web python -c "
import boto3
from django.conf import settings
s3 = boto3.client('s3', 
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
print(s3.list_buckets())
"
```

#### 4. مشکل SSL

```bash
# بررسی گواهی‌نامه
openssl x509 -in ssl/cert.pem -text -noout

# تست SSL
curl -I https://your-domain.com

# تجدید گواهی Let's Encrypt
certbot renew
```

### کامندهای مفید

```bash
# ری‌استارت کامل سیستم
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# بروزرسانی تصاویر
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# پاک‌سازی تصاویر قدیمی
docker system prune -a

# مشاهده استفاده منابع
docker stats

# Export/Import دیتابیس
docker-compose -f docker-compose.prod.yml exec db pg_dump -U soapify soapify > backup.sql
docker-compose -f docker-compose.prod.yml exec -T db psql -U soapify soapify < backup.sql
```

## 📈 بهینه‌سازی Performance

### تنظیمات Django

```python
# در settings.py
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60
```

### تنظیمات Celery

```python
# تنظیم بهینه worker ها
CELERY_WORKER_CONCURRENCY = 4
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
```

### تنظیمات Nginx

```nginx
worker_processes auto;
worker_connections 1024;

# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_comp_level 6;

# Caching
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 🔄 بروزرسانی

### بروزرسانی کد

```bash
# دریافت آخرین تغییرات
git pull origin main

# بروزرسانی با downtime کم
./scripts/deploy.sh production your-domain.com
```

### بروزرسانی پایگاه داده

```bash
# اجرای migration ها
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# بررسی وضعیت migration ها
docker-compose -f docker-compose.prod.yml exec web python manage.py showmigrations
```

### Rolling Update (بدون downtime)

```bash
# بروزرسانی تدریجی سرویس‌ها
docker-compose -f docker-compose.prod.yml up -d --no-deps web
docker-compose -f docker-compose.prod.yml up -d --no-deps celery-worker
```

## 📞 پشتیبانی

### مخاطبین اضطراری

- سیستم ادمین: <admin@soapify.com>

- DevOps: <devops@soapify.com>

- پشتیبانی 24/7: <+98-912-345-6789>

### مستندات اضافی

- [API Documentation](API_DOCUMENTATION.md)
- [User Manual](USER_MANUAL.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

### منابع خارجی

- [Django Deployment](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Configuration](https://nginx.org/en/docs/)

---

### _موفق باشید! 🎉_

پس از دیپلوی موفق، سیستم SOAPify آماده استفاده است. حتماً پسورد admin را تغییر دهید و تنظیمات امنیتی را بررسی کنید.
