# راهنمای سریع دیپلوی SOAPify

## 🚀 دیپلوی در 5 دقیقه

### مرحله 1: آماده‌سازی سرور
```bash
# در سرور Ubuntu 22.04
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
# Logout و دوباره login کنید
```

### مرحله 2: دانلود پروژه
```bash
git clone <repository-url>
cd soapify
chmod +x scripts/*.sh entrypoint.sh
```

### مرحله 3: تنظیمات محیط
```bash
# کپی فایل نمونه
cp .env.prod.example .env.prod

# ویرایش با nano یا vim
nano .env.prod

# حداقل این موارد را تنظیم کنید:
# - SECRET_KEY (تولید کنید)
# - DATABASE passwords
# - ALLOWED_HOSTS با دامنه شما
# - S3 credentials
# - API keys
```

### مرحله 4: SSL (اختیاری اما توصیه می‌شود)
```bash
# Let's Encrypt
sudo apt install certbot
certbot certonly --standalone -d your-domain.com

# کپی certificates
mkdir -p ssl
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

### مرحله 5: دیپلوی!
```bash
./scripts/deploy.sh production your-domain.com
```

## ✅ بررسی سلامت

بعد از دیپلوی:
```bash
# بررسی سرویس‌ها
docker-compose -f docker-compose.prod.yml ps

# بررسی logs
docker-compose -f docker-compose.prod.yml logs -f

# تست endpoint
curl https://your-domain.com/healthz
```

## 🔑 دسترسی‌ها

- **Application**: https://your-domain.com
- **Admin Panel**: https://your-domain.com/admin/
- **API Docs**: https://your-domain.com/redoc/
- **Default Admin**: admin / admin123 (حتماً تغییر دهید!)

## ⚠️ نکات مهم

1. **کلیدهای امنیتی را تولید کنید**:
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

2. **پسورد admin را تغییر دهید**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py changepassword admin
   ```

3. **Backup فعال کنید**:
   ```bash
   crontab -e
   # اضافه کنید:
   0 2 * * * /path/to/soapify/scripts/backup.sh
   ```

## 🆘 مشکلات رایج

### پایگاه داده وصل نمی‌شود
```bash
docker-compose -f docker-compose.prod.yml logs db
# بررسی پسورد و connection string
```

### Static files نمایش داده نمی‌شوند
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker-compose -f docker-compose.prod.yml restart nginx
```

### SSL کار نمی‌کند
```bash
# بررسی certificates
ls -la ssl/
# بررسی nginx config
docker-compose -f docker-compose.prod.yml logs nginx
```

---

**موفق باشید! 🎉**