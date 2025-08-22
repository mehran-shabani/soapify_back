# Server Monitoring System

سیستم مانیتورینگ سمت سرور برای تست و نظارت بر API های Soapify.

## ویژگی‌ها

- ✅ مانیتورینگ real-time منابع سیستم (CPU, Memory, Disk)
- ✅ تست خودکار API ها در بازه‌های زمانی مشخص
- ✅ تست‌های کارایی و Load Testing
- ✅ ذخیره نتایج در دیتابیس
- ✅ سیستم هشدار برای مشکلات
- ✅ داشبورد وب برای مشاهده نتایج
- ✅ یکپارچه‌سازی با Prometheus و Grafana

## نصب و راه‌اندازی

### با استفاده از Docker:

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### دسترسی به سرویس‌ها:

- **Monitoring Dashboard**: http://localhost:8080
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### بدون Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m uvicorn src.main:app --host 0.0.0.0 --port 8080
```

## تنظیمات

ایجاد فایل `.env` برای تنظیمات:

```env
API_BASE_URL=https://django-m.chbk.app
TEST_INTERVAL_MINUTES=5
ALERT_RESPONSE_TIME_MS=1000
ALERT_ERROR_RATE_PERCENT=5.0
```

## استفاده

### از طریق داشبورد وب:

1. مرورگر را باز کرده و به آدرس http://localhost:8080 بروید
2. روی دکمه "اجرای همه تست‌ها" کلیک کنید
3. نتایج را در بخش‌های مختلف مشاهده کنید

### از طریق API:

```bash
# Run all tests
curl -X POST http://localhost:8080/api/test/all

# Run specific test
curl -X POST http://localhost:8080/api/test/voice
curl -X POST http://localhost:8080/api/test/stt
curl -X POST http://localhost:8080/api/test/checklist

# Load test
curl -X POST "http://localhost:8080/api/test/load/checklist?concurrent_requests=20"

# Get system metrics
curl http://localhost:8080/api/metrics/system

# Get performance metrics
curl http://localhost:8080/api/metrics/performance?hours=24

# Get alerts
curl http://localhost:8080/api/alerts
```

## ساختار دیتابیس

نتایج تست‌ها در جداول زیر ذخیره می‌شوند:

- `test_runs`: اطلاعات کلی هر تست
- `voice_test_results`: نتایج تست‌های آپلود صدا
- `performance_metrics`: معیارهای کارایی سیستم
- `alerts`: هشدارهای سیستم

## توسعه

برای اضافه کردن تست‌های جدید:

1. کلاس تست جدید در `src/api_tests.py` ایجاد کنید
2. endpoint مربوطه را در `src/main.py` اضافه کنید
3. UI را در `templates/dashboard.html` بروزرسانی کنید

## Monitoring با Grafana

داشبوردهای آماده Grafana در پوشه `grafana/dashboards` قرار دارند که شامل:

- System Metrics Dashboard
- API Performance Dashboard
- Alert Dashboard