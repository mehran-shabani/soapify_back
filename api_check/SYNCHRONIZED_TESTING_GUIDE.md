# راهنمای تست همزمان Frontend و Server

این راهنما نحوه استفاده از قابلیت جدید تست همزمان بین Frontend (خانه) و Server Monitoring را توضیح می‌دهد.

## 🎯 هدف

امکان اجرای تست‌های API به صورت همزمان از دو نقطه مختلف:
- **Frontend**: از کامپیوتر شخصی در خانه
- **Server**: از سرور که API روی آن قرار دارد

## 🚀 راه‌اندازی

### 1. راه‌اندازی Server Monitoring (روی سرور)

```bash
# SSH به سرور
ssh user@your-server-ip

# Clone پروژه
git clone [your-repo]
cd api_check

# اجرای اسکریپت
./start-testing.sh
# گزینه 1 را انتخاب کنید
```

### 2. راه‌اندازی Frontend Testing (در خانه)

```bash
# در سیستم محلی
cd api_check

# ویرایش فایل تنظیمات
cd front_check_server
cp .env.example .env
# در .env آدرس سرور را وارد کنید:
# SERVER_MONITOR_URL=http://your-server-ip:8080

# اجرای اسکریپت
./start-testing.sh
# گزینه 2 را انتخاب کنید
```

## 📡 قابلیت‌های تست همزمان

### 1. تست Synchronized (همگام‌سازی شده)
- ابتدا تست‌ها در Frontend اجرا می‌شود
- نتایج به Server ارسال می‌شود
- Server همان تست‌ها را اجرا می‌کند
- نتایج مقایسه می‌شود

### 2. تست Parallel (موازی)
- تست‌ها همزمان در Frontend و Server اجرا می‌شود
- زمان اجرا کمتر است
- مناسب برای تست‌های Load

## 🖥️ استفاده از رابط کاربری

1. **وارد React App شوید**: http://localhost:3000

2. **به تب "تست همزمان" بروید**

3. **نوع تست را انتخاب کنید**:
   - Synchronized: برای مقایسه دقیق نتایج
   - Parallel: برای تست سرعت و کارایی

4. **دکمه اجرا را بزنید**

## 📊 تحلیل نتایج

### نتایج نمایش داده شده:

1. **نتایج Frontend**: 
   - زمان پاسخ از دید کاربر
   - وضعیت اتصال شبکه
   - کیفیت ارسال/دریافت

2. **نتایج Server**:
   - زمان پردازش واقعی
   - منابع مصرفی
   - وضعیت سیستم

3. **مقایسه**:
   - تفاوت زمان‌های پاسخ
   - ناهماهنگی‌ها
   - مشکلات احتمالی شبکه

### تفسیر ناهماهنگی‌ها:

- **تفاوت زمان زیاد**: مشکل شبکه یا تاخیر
- **نتایج متفاوت**: مشکل در API یا کش
- **خطا در یک طرف**: مشکل دسترسی یا فایروال

## 🔧 تنظیمات پیشرفته

### تغییر Endpoint سرور:
```javascript
// در فایل front_check_server/react_app/src/services/serverSync.js
const SERVER_MONITOR_URL = process.env.REACT_APP_SERVER_MONITOR_URL || 'http://your-server:8080';
```

### افزودن تست جدید:
1. در `apiService.js` سرویس جدید اضافه کنید
2. در `server_check_server/src/api_tests.py` تست متناظر بسازید
3. در `SynchronizedTester.js` به لیست اضافه کنید

## 🚨 عیب‌یابی

### مشکل: عدم اتصال به سرور
```bash
# بررسی firewall
sudo ufw allow 8080

# بررسی Docker
docker ps
docker-compose logs monitor
```

### مشکل: CORS Error
```python
# در server_check_server/src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://your-ip:3000"],
    # ...
)
```

### مشکل: تست‌ها اجرا نمی‌شود
- مطمئن شوید هر دو سرویس در حال اجرا هستند
- لاگ‌ها را بررسی کنید: `docker-compose logs -f`

## 📈 مزایای این روش

1. **تست واقعی**: شرایط واقعی کاربر را شبیه‌سازی می‌کند
2. **تشخیص مشکلات شبکه**: تفاوت‌های زمانی را نشان می‌دهد
3. **مانیتورینگ دوطرفه**: هم از دید کاربر و هم سرور
4. **اتوماسیون**: امکان اجرای خودکار تست‌ها

## 🎉 نمونه استفاده

```bash
# روی سرور
cd api_check/server_check_server
docker-compose up -d

# در خانه
cd api_check/front_check_server
echo "SERVER_MONITOR_URL=http://185.123.456.789:8080" > .env
docker-compose up -d

# باز کردن مرورگر
open http://localhost:3000

# رفتن به تب "تست همزمان"
# کلیک روی "اجرای تست همزمان"
# مشاهده نتایج مقایسه‌ای
```

اکنون می‌توانید از خانه به سرور دستور دهید و تست‌ها را به صورت همزمان اجرا کنید! 🚀