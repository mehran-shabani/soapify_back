# SOAPify Deployment Checklist

## 📋 Pre-Deployment Checklist

### 1. Environment Setup
- [ ] Copy `.env.prod.example` to `.env.prod`
- [ ] Generate secure `SECRET_KEY` (use: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
- [ ] Generate secure `HMAC_SHARED_SECRET` (use: `openssl rand -base64 32`)
- [ ] Generate secure `LOCAL_JWT_SECRET` (use: `openssl rand -base64 32`)
- [ ] Update all production passwords in `.env.prod`
- [ ] Set correct `ALLOWED_HOSTS` with your domain
- [ ] Configure `CORS_ALLOWED_ORIGINS` with your frontend URL

### 2. Database Configuration
- [ ] Set strong `POSTGRES_PASSWORD` in `.env.prod`
- [ ] Verify `DATABASE_URL` matches PostgreSQL credentials
- [ ] Create database backup strategy
- [ ] Test database connection

### 3. S3 Storage Setup
- [ ] Create S3 bucket for production
- [ ] Configure S3 IAM user with appropriate permissions
- [ ] Set `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY`
- [ ] Set correct `S3_BUCKET_NAME` and `S3_REGION_NAME`
- [ ] Test S3 connection and permissions

### 4. External Services
- [ ] Configure OpenAI/GapGPT API credentials
- [ ] Set up Helssa integration credentials
- [ ] Configure Crazy Miner SMS service
- [ ] Test all external service connections

### 5. SSL/TLS Configuration
- [ ] Obtain SSL certificates (Let's Encrypt or commercial)
- [ ] Place certificates in `ssl/` directory:
  - [ ] `ssl/cert.pem` (certificate)
  - [ ] `ssl/key.pem` (private key)
- [ ] Update nginx configuration with SSL settings
- [ ] Enable `SECURE_SSL_REDIRECT=True` in production

### 6. Security Hardening
- [ ] Change default Django admin credentials
- [ ] Set `DEBUG=False` in production
- [ ] Configure firewall rules (ports 80, 443, 22 only)
- [ ] Enable all security headers in settings
- [ ] Set up fail2ban for SSH protection
- [ ] Configure rate limiting

## 🚀 Deployment Steps

### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
```

### 2. Deploy Application
```bash
# Clone repository
git clone <repository-url>
cd soapify

# Set up environment
cp .env.prod.example .env.prod
# Edit .env.prod with production values

# Make scripts executable
chmod +x scripts/*.sh entrypoint.sh

# Run deployment
./scripts/deploy.sh production your-domain.com
```

### 3. Post-Deployment Verification
```bash
# Check service health
./scripts/health_check.sh production

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Test endpoints
curl https://your-domain.com/healthz
curl https://your-domain.com/api/auth/token/
```

## 🔍 Post-Deployment Checklist

### 1. Functionality Testing
- [ ] Test user registration and login
- [ ] Test JWT token generation and refresh
- [ ] Test audio file upload
- [ ] Test STT processing
- [ ] Test SOAP note generation
- [ ] Test PDF/Markdown export
- [ ] Test SMS sending
- [ ] Test search functionality
- [ ] Test admin panel access

### 2. Performance Verification
- [ ] Check response times for key endpoints
- [ ] Monitor CPU and memory usage
- [ ] Check database query performance
- [ ] Verify Redis caching is working
- [ ] Test Celery task processing

### 3. Security Verification
- [ ] Verify SSL certificate is valid
- [ ] Test HTTPS redirect
- [ ] Check security headers
- [ ] Verify CORS configuration
- [ ] Test rate limiting
- [ ] Scan for vulnerabilities

### 4. Monitoring Setup
- [ ] Configure system monitoring (CPU, memory, disk)
- [ ] Set up application logging
- [ ] Configure error tracking (Sentry)
- [ ] Set up uptime monitoring
- [ ] Configure alert notifications
- [ ] Access Flower at https://flower.your-domain.com

### 5. Backup Configuration
- [ ] Set up automated database backups
- [ ] Configure S3 backup retention
- [ ] Test backup restoration
- [ ] Document recovery procedures

## 📊 Monitoring URLs

After deployment, access these URLs:
- Main Application: `https://your-domain.com`
- Admin Panel: `https://your-domain.com/admin/`
- Admin Plus: `https://your-domain.com/adminplus/`
- API Documentation: `https://your-domain.com/redoc/`
- Health Check: `https://your-domain.com/healthz/`
- Flower (Celery): `https://flower.your-domain.com` (if configured)

## 🔧 Common Issues and Solutions

### Database Connection Issues
```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready -U soapify

# View database logs
docker-compose -f docker-compose.prod.yml logs db
```

### Celery Worker Issues
```bash
# Check worker status
docker-compose -f docker-compose.prod.yml exec web celery -A soapify inspect active

# Restart workers
docker-compose -f docker-compose.prod.yml restart celery-worker-default
```

### SSL Certificate Issues
```bash
# Test SSL
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Renew Let's Encrypt
certbot renew --force-renewal
```

### Container Issues
```bash
# View all containers
docker-compose -f docker-compose.prod.yml ps

# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

## 📝 Final Notes

1. **Change Default Passwords**: Immediately change all default passwords after first login
2. **Enable 2FA**: Consider enabling two-factor authentication for admin accounts
3. **Regular Updates**: Schedule regular updates for security patches
4. **Monitoring**: Set up 24/7 monitoring and alerts
5. **Documentation**: Keep deployment documentation updated

## ✅ Sign-off

- [ ] All checklist items completed
- [ ] System tested and verified
- [ ] Backups configured and tested
- [ ] Monitoring active
- [ ] Documentation updated
- [ ] Team trained on procedures

**Deployment Date**: _______________
**Deployed By**: _______________
**Verified By**: _______________