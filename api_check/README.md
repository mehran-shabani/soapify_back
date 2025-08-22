# API Testing System for Soapify

این سیستم برای تست جامع API های Soapify طراحی شده و شامل دو بخش اصلی است:

## ساختار پروژه

```
api_check/
├── front_check_server/    # تست‌های سمت کلاینت (Flutter/React)
│   ├── flutter_app/       # اپلیکیشن Flutter برای تست موبایل
│   ├── react_app/         # اپلیکیشن React برای تست وب
│   └── test_results/      # نتایج تست‌ها
│
└── server_check_server/   # مانیتورینگ سمت سرور
    ├── monitoring/        # سیستم مانیتورینگ
    ├── performance/       # تست‌های کارایی
    └── reports/           # گزارش‌ها
```

## قابلیت‌های تست

### 1. تست‌های ضبط صدا (Voice Recording)
- کیفیت صدا (Sample Rate, Bit Rate)
- حجم فایل
- زمان آپلود
- فرمت‌های مختلف (WAV, MP3, M4A)

### 2. تست‌های تبدیل گفتار به متن (STT)
- دقت تشخیص
- زمان پردازش
- پشتیبانی از زبان‌های مختلف

### 3. تست‌های چک‌لیست
- ایجاد چک‌لیست
- آپدیت وضعیت
- همگام‌سازی

### 4. تست‌های کارایی
- زمان پاسخ (Response Time)
- تعداد درخواست‌های همزمان
- استفاده از منابع سرور

## نحوه اجرا

### بخش Frontend (روی سیستم محلی):
```bash
cd front_check_server
docker-compose up -d
# سپس در مرورگر: http://localhost:3000
```

### بخش Server (روی سرور):
```bash
cd server_check_server
docker-compose up -d
# داشبورد مانیتورینگ: http://your-server:8080
```

## Base URL
```
https://django-m.chbk.app/
```