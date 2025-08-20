# راهنمای سیستم پرداخت CrazyMiner

## معرفی
سیستم پرداخت CrazyMiner برای مدیریت پرداخت‌ها از طریق سرور خارجی (api.medogram.ir) طراحی شده است. این سیستم اطلاعات کاربران را از سرور اصلی دریافت می‌کند و پرداخت‌ها را با رمزنگاری ساده مدیریت می‌کند.

## ویژگی‌ها
- دریافت اطلاعات کاربر از سرور خارجی
- رمزنگاری اطلاعات حساس کاربران
- ایجاد و پیگیری تراکنش‌های پرداخت
- ثبت لاگ کامل از تمام فعالیت‌ها
- پشتیبانی از callback درگاه پرداخت

## نصب و راه‌اندازی

### 1. نصب وابستگی‌ها
```bash
pip install cryptography
```

### 2. تنظیمات محیطی
در فایل `.env` یا متغیرهای محیطی:
```env
PAYMENT_GATEWAY_URL=https://api.medogram.ir
PAYMENT_API_KEY=your_api_key_here
PAYMENT_REDIRECT_URL=https://your-domain.com/payment-redirect/
```

### 3. اجرای migration
```bash
python manage.py makemigrations
python manage.py migrate
```

## نقاط پایانی API

### 1. ایجاد پرداخت
```
POST /crazyminer/payment/create/
```

Body (JSON):
```json
{
    "amount": 100000,
    "description": "توضیحات پرداخت",
    "user_identifier": "09123456789"
}
```

Response:
```json
{
    "transaction_id": "uuid-here",
    "payment_url": "https://api.medogram.ir/payment/gateway-123-get",
    "amount": 100000,
    "status": "processing",
    "status_display": "در حال پردازش"
}
```

### 2. Callback درگاه
```
POST /crazyminer/payment/callback/
```

Body (از طرف درگاه):
```json
{
    "trans_id": "transaction-reference",
    "id_get": "payment-id",
    "tracking_code": "optional-tracking-code"
}
```

### 3. بررسی وضعیت پرداخت
```
GET /crazyminer/payment/status/<transaction_id>/
```

Response:
```json
{
    "transaction_id": "uuid-here",
    "status": "completed",
    "status_display": "تکمیل شده",
    "amount": 100000,
    "gateway_tracking_code": "tracking-code",
    "created_at": "2024-01-01T12:00:00Z",
    "completed_at": "2024-01-01T12:05:00Z"
}
```

### 4. لیست پرداخت‌ها (نیاز به احراز هویت)
```
GET /crazyminer/payment/list/
```

## مدل‌های داده

### CrazyMinerPayment
- ذخیره اطلاعات اصلی تراکنش
- وضعیت‌ها: pending, processing, completed, failed, cancelled
- رمزنگاری اطلاعات کاربر در فیلد encrypted_user_data

### CrazyMinerPaymentLog
- ثبت تمام فعالیت‌های مربوط به پرداخت
- انواع لاگ: request, callback, verification, user_fetch, error

## امنیت

### رمزنگاری
- استفاده از Fernet برای رمزنگاری متقارن
- کلید رمزنگاری از SECRET_KEY جنگو مشتق می‌شود
- اطلاعات حساس کاربر قبل از ذخیره رمزنگاری می‌شوند

### نکات امنیتی
1. حتماً PAYMENT_API_KEY را در محیط production تنظیم کنید
2. از HTTPS برای تمام ارتباطات استفاده کنید
3. لاگ‌ها را مرتب بررسی کنید
4. callback URLs را محدود کنید

## عیب‌یابی

### خطاهای رایج
1. **خطای اتصال به درگاه**: بررسی کنید PAYMENT_GATEWAY_URL صحیح باشد
2. **خطای احراز هویت**: مطمئن شوید PAYMENT_API_KEY تنظیم شده است
3. **خطای رمزنگاری**: بررسی کنید SECRET_KEY جنگو تنظیم شده باشد

### لاگ‌ها
لاگ‌های پرداخت در:
- Console output
- فایل لاگ پروژه (طبق تنظیمات LOGGING)

## نمونه کد استفاده

### Python/requests
```python
import requests

# ایجاد پرداخت
response = requests.post(
    'https://your-domain.com/crazyminer/payment/create/',
    json={
        'amount': 100000,
        'description': 'خرید اشتراک',
        'user_identifier': '09123456789'
    }
)

if response.status_code == 201:
    data = response.json()
    payment_url = data['payment_url']
    # کاربر را به payment_url هدایت کنید
```

### JavaScript/fetch
```javascript
// ایجاد پرداخت
fetch('/crazyminer/payment/create/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        amount: 100000,
        description: 'خرید اشتراک',
        user_identifier: '09123456789'
    })
})
.then(response => response.json())
.then(data => {
    // کاربر را به data.payment_url هدایت کنید
    window.location.href = data.payment_url;
});
```