# Frontend Testing System

سیستم تست API از سمت کلاینت برای Soapify که شامل React app و در آینده Flutter app خواهد بود.

## ویژگی‌ها

### React Testing App:
- ✅ تست کامل API ها (Voice Upload, STT, Checklist)
- ✅ ضبط صدا و آپلود مستقیم از مرورگر
- ✅ تست بار (Load Testing) با درخواست‌های همزمان
- ✅ داشبورد آماری با نمودارهای تعاملی
- ✅ ذخیره نتایج در localStorage
- ✅ دانلود نتایج به صورت JSON

## نصب و اجرا

### با Docker (توصیه می‌شود):

```bash
# Build and run
docker-compose up -d

# مشاهده لاگ‌ها
docker-compose logs -f

# توقف سرویس‌ها
docker-compose down
```

### بدون Docker:

```bash
# وارد پوشه React app شوید
cd react_app

# نصب وابستگی‌ها
npm install

# اجرای برنامه در حالت توسعه
npm start

# ساخت نسخه production
npm run build
```

## دسترسی به برنامه

- **React App**: http://localhost:3000
- **Test File Server**: http://localhost:8081

## استفاده از React App

### 1. تست‌های خودکار:
- روی دکمه "اجرای همه تست‌ها" کلیک کنید
- نتایج به صورت خودکار نمایش داده می‌شود

### 2. ضبط و آپلود صدا:
1. به تب "ضبط صدا" بروید
2. دکمه "شروع ضبط" را بزنید
3. صحبت کنید
4. "توقف ضبط" را بزنید
5. می‌توانید صدا را پخش کنید
6. "آپلود صدا" را برای ارسال به سرور بزنید

### 3. تست بار:
1. به تب "تست بار" بروید
2. سرویس مورد نظر را انتخاب کنید
3. تعداد درخواست‌های همزمان را تنظیم کنید
4. "شروع تست بار" را بزنید

### 4. داشبورد:
- آمار کلی تست‌ها
- نمودار دایره‌ای نسبت موفقیت/شکست
- نمودار میله‌ای زمان پاسخ API ها
- جزئیات آماری هر API

## ساختار پروژه

```
front_check_server/
├── react_app/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── VoiceRecorder.js
│   │   │   ├── TestResults.js
│   │   │   ├── LoadTester.js
│   │   │   └── Dashboard.js
│   │   ├── services/
│   │   │   └── apiService.js
│   │   ├── App.js
│   │   └── index.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── flutter_app/         # (در حال توسعه)
├── test_files/          # فایل‌های تست
└── docker-compose.yml
```

## تنظیمات

می‌توانید URL سرور API را در فایل docker-compose.yml تغییر دهید:

```yaml
environment:
  - REACT_APP_API_URL=https://django-m.chbk.app
```

## توسعه

### اضافه کردن تست جدید:

1. سرویس جدید را در `apiService.js` اضافه کنید
2. کامپوننت تست را بسازید
3. به `App.js` اضافه کنید

### تغییر استایل:

از `styled-components` استفاده شده است. می‌توانید استایل‌ها را مستقیماً در کامپوننت‌ها تغییر دهید.

## نکات

- برای ضبط صدا، مرورگر باید دسترسی به میکروفون داشته باشد
- نتایج تست‌ها در localStorage ذخیره می‌شود
- می‌توانید نتایج را به صورت JSON دانلود کنید
- برای تست بار، مراقب باشید تعداد زیادی درخواست همزمان ارسال نکنید