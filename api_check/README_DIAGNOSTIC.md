# 🔧 سیستم تشخیص و رفع خطای API

## نمای کلی

این سیستم برای شناسایی خودکار مشکلات API و ارائه راه‌حل‌های عملی طراحی شده است. هنگامی که خطایی رخ می‌دهد، سیستم:

1. **تشخیص خودکار**: نوع و سطح مشکل را شناسایی می‌کند
2. **دستورات آماده**: دستورات ترمینال مناسب برای Desktop و Server ارائه می‌دهد
3. **راهنمای گام به گام**: مراحل رفع مشکل را نشان می‌دهد
4. **بهینه‌سازی**: پیشنهاد بهبود عملکرد API ارائه می‌دهد

## سطوح مشکلات

### 🟢 سطح سبز (قابل حل توسط شما)
- مشکلات شبکه محلی
- تنظیمات مرورگر
- Environment variables
- Docker محلی

### 🟡 سطح زرد (نیاز به همکاری)
- تنظیمات CORS
- مجوزهای API
- Rate limiting
- احراز هویت

### 🔴 سطح قرمز (فقط Admin سرور)
- Server down
- مشکلات دیتابیس
- گواهی SSL
- قوانین فایروال

## نحوه استفاده

### 1. تشخیص خودکار خطا

وقتی خطایی رخ می‌دهد، به صورت خودکار به تب "تشخیص خطا" منتقل می‌شوید:

```javascript
// مثال خطای CORS
Access to XMLHttpRequest at 'https://django-m.chbk.app/api/v1/voice/upload/' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

### 2. دریافت دستورات Desktop

دستوراتی که خودتان می‌توانید اجرا کنید:

#### Windows (PowerShell):
```powershell
# بررسی اتصال
ping django-m.chbk.app

# تست CORS
Invoke-WebRequest -Uri "https://django-m.chbk.app/api/v1/voice/upload/" `
  -Method OPTIONS `
  -Headers @{
    "Origin" = "http://localhost:3000"
    "Access-Control-Request-Method" = "POST"
  }
```

#### macOS/Linux:
```bash
# بررسی اتصال
ping -c 4 django-m.chbk.app

# تست CORS
curl -X OPTIONS https://django-m.chbk.app/api/v1/voice/upload/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" -v
```

### 3. دستورات Server (برای Admin)

دستوراتی که باید روی سرور اجرا شوند:

```bash
# بررسی وضعیت Docker
docker ps -a | grep soapify

# بررسی لاگ‌ها
docker logs --tail 50 soapify_web

# بررسی تنظیمات CORS
docker exec soapify_web python manage.py shell -c \
  "from django.conf import settings; print(settings.CORS_ALLOWED_ORIGINS)"

# اضافه کردن Origin جدید
docker exec soapify_web python manage.py shell << EOF
from django.conf import settings
settings.CORS_ALLOWED_ORIGINS.append('http://localhost:3000')
EOF
```

## قابلیت‌های ویژه

### 1. دنباله تست (Test Sequence)

برای debug کامل یک endpoint:

```bash
# گام 1: بررسی اتصال
ping django-m.chbk.app

# گام 2: بررسی HTTPS
curl -I https://django-m.chbk.app

# گام 3: تست API endpoint
curl -X GET https://django-m.chbk.app/api/v1/voice/upload/

# گام 4: بررسی CORS
curl -X OPTIONS https://django-m.chbk.app/api/v1/voice/upload/ \
  -H "Origin: http://localhost:3000" -v
```

### 2. اسکریپت‌های Quick Fix

#### غیرفعال کردن CORS در Chrome:

Windows:
```powershell
start chrome.exe --user-data-dir="C:/Chrome dev session" --disable-web-security
```

macOS:
```bash
open -n -a /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --args --disable-web-security --user-data-dir="/tmp/chrome_test"
```

#### استفاده از پروکسی محلی:
```bash
npx local-cors-proxy --proxyUrl https://django-m.chbk.app --port 8010
```

### 3. بهینه‌سازی API

سیستم می‌تواند روش‌های مختلف پیاده‌سازی را تست کند:

1. **Voice Upload**:
   - Standard
   - Compressed
   - Streaming

2. **Speech to Text**:
   - Direct
   - Preprocessed
   - Chunked

3. **Database**:
   - Default
   - Optimized Read
   - Optimized Write

## رفع مشکلات رایج

### مشکل: CORS Policy Block

**راه حل Desktop:**
```bash
# استفاده از پروکسی محلی
npx local-cors-proxy --proxyUrl https://django-m.chbk.app --port 8010
```

**راه حل Server:**
```bash
# در فایل settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]
```

### مشکل: Connection Timeout

**راه حل Desktop:**
```bash
# بررسی فایروال
# Windows
netsh advfirewall show allprofiles

# macOS/Linux
sudo iptables -L
```

**راه حل Server:**
```bash
# بررسی پورت‌ها
sudo netstat -tuln | grep 8000

# ری‌استارت سرویس
docker-compose restart web
```

### مشکل: 401 Unauthorized

**راه حل Desktop:**
```bash
# دریافت توکن جدید
curl -X POST https://django-m.chbk.app/api/token/ \
  -d "username=test&password=test"
```

**راه حل Server:**
```bash
# ایجاد کاربر جدید
docker exec soapify_web python manage.py createsuperuser
```

## نکات مهم

1. **همیشه ابتدا دستورات Desktop را امتحان کنید**
2. **دستورات Server را دقیقاً کپی کنید**
3. **قبل از اجرای دستورات، backup بگیرید**
4. **لاگ‌ها را ذخیره کنید برای بررسی بعدی**

## ارتباط با تیم

اگر مشکل حل نشد:

1. اسکرین‌شات از خطا بگیرید
2. دستورات اجرا شده و نتایج را کپی کنید
3. با تیم DevOps تماس بگیرید
4. شماره تیکت را یادداشت کنید