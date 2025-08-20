# خلاصه راه‌اندازی Redocly Classic Catalog برای SOAPify

## کارهای انجام شده

### 1. ساختار پوشه‌ها
```
/workspace/
├── apis/
│   ├── auth/
│   │   └── auth-api.yaml (احراز هویت با شماره تلفن و OTP)
│   ├── analytics/
│   │   └── analytics-api.yaml (تحلیل داده و گزارش‌گیری)
│   ├── integrations/
│   │   └── helssa-api.yaml (یکپارچه‌سازی با Helssa)
│   └── soapify-main-api.yaml (APIهای اصلی SOAPify)
├── images/
│   ├── logo.svg
│   └── api-icon.png
├── redocly.yaml (پیکربندی اصلی)
├── sidebars.yaml (پیکربندی سایدبار)
└── index.md (صفحه اصلی)
```

### 2. ویژگی‌های پیاده‌سازی شده

#### احراز هویت با شماره تلفن (Phone + OTP)
- ارسال کد تأیید به شماره تلفن
- ثبت‌نام با شماره تلفن و کد تأیید
- ورود با شماره تلفن (بدون نیاز به رمز عبور)
- مدیریت توکن JWT

#### Classic Catalog
- کاتالوگ قابل جستجو با فیلترهای پیشرفته
- فیلتر بر اساس:
  - حوزه عملکرد (authentication, core, analytics, integrations)
  - وضعیت توسعه (stable, active, beta, deprecated)
  - دسته‌بندی (main, core, auxiliary, external)

#### متادیتای APIها
هر فایل OpenAPI دارای بخش `x-metadata` است:
```yaml
x-metadata:
  type: openapi
  tags: [stable, active]
  capability: authentication
  category: core
```

### 3. نحوه استفاده

#### مشاهده محلی
```bash
# نصب Redocly CLI
npm install -g @redocly/cli

# پیش‌نمایش زنده
redocly preview-docs

# ساخت فایل استاتیک
redocly build-docs
```

#### دسترسی به کاتالوگ
- کاتالوگ APIها در مسیر `/apis/` قابل دسترسی است
- فیلترها به صورت خودکار از متادیتای APIها ساخته می‌شوند

### 4. نکات مهم

#### شماره تلفن در مدل User
- فیلد `phone_number` در مدل User ضروری است
- فرمت بین‌المللی: `+989123456789`
- پشتیبانی از کدهای کشورهای مختلف

#### فرآیند احراز هویت
1. کاربر شماره تلفن خود را وارد می‌کند
2. سیستم کد 6 رقمی ارسال می‌کند (اعتبار 15 دقیقه)
3. کاربر کد را وارد می‌کند
4. در صورت تطابق، توکن JWT صادر می‌شود
5. توکن دسترسی: 2 روز اعتبار
6. توکن تازه‌سازی: 10 روز اعتبار

### 5. گسترش آینده

برای افزودن API جدید:
1. فایل OpenAPI در پوشه مناسب در `apis/` ایجاد کنید
2. متادیتای مناسب اضافه کنید
3. در `redocly.yaml` بخش `apis` را به‌روزرسانی کنید

### 6. فایل‌های تولید شده
- `redoc-static.html`: مستندات استاتیک قابل میزبانی
- قابل استفاده در هر وب سرور بدون نیاز به Node.js

## دستورات مفید

```bash
# اعتبارسنجی فایل‌های OpenAPI
redocly lint

# ساخت مستندات با تم سفارشی
redocly build-docs --theme.rightToLeft true

# پیش‌نمایش با پورت سفارشی
redocly preview-docs --port 3000
```