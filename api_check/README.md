# API Testing System for Soapify

این سیستم برای تست جامع API های Soapify طراحی شده و شامل دو بخش اصلی است:

## ساختار پروژه

```
api_check/
├── front_check_server/     # سیستم تست سمت کلاینت (React)
│   ├── react_app/         # اپلیکیشن React
│   ├── docker-compose.yml
│   └── README.md
├── server_check_server/    # سیستم مانیتورینگ سمت سرور (FastAPI)
│   ├── src/              # کد منبع FastAPI
│   ├── docker-compose.yml
│   └── README.md
├── start-testing.sh      # اسکریپت راه‌اندازی سریع
├── README_SYNC.md        # راهنمای تست همزمان
├── README_DIAGNOSTIC.md  # راهنمای سیستم تشخیص خطا
└── README.md            # این فایل
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

### راه‌اندازی سریع
```bash
./start-testing.sh
```
این اسکریپت از شما می‌پرسد کدام بخش را می‌خواهید اجرا کنید.

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
# داشبورد مانیتورینگ: http://your-server:8001
```

## قابلیت‌های جدید

### 🔧 سیستم تشخیص و رفع خطا
- تشخیص خودکار نوع خطا
- ارائه دستورات ترمینال برای Desktop و Server
- دسته‌بندی مشکلات (سبز/زرد/قرمز)
- راهنمای گام به گام رفع مشکل

### 🔄 تست همزمان (Synchronized Testing)
- اجرای همزمان تست‌ها در Frontend و Server
- مقایسه نتایج و شناسایی اختلافات
- نمایش وضعیت real-time

### 🚀 بهینه‌سازی خودکار API
- تست روش‌های مختلف پیاده‌سازی
- انتخاب بهترین پیکربندی
- تولید پروژه بهینه شده (ZIP)

برای اطلاعات بیشتر:
- [راهنمای تست همزمان](README_SYNC.md)
- [راهنمای سیستم تشخیص خطا](README_DIAGNOSTIC.md)

## Base URL
```
https://django-m.chbk.app/
```