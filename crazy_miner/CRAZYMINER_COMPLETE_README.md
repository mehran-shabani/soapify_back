# راهنمای کامل CrazyMiner

## معرفی
CrazyMiner یک سیستم واسط برای پزشکان است که دو عملکرد اصلی دارد:
1. دسترسی امن به اطلاعات بیماران از SOAPify
2. انجام پرداخت برای کاربران SOAPify

## عملکردها

### 1. دسترسی به اطلاعات بیمار

#### فرآیند:
1. پزشک شماره موبایل بیمار را وارد می‌کند
2. کد OTP به موبایل بیمار ارسال می‌شود
3. پزشک کد را از بیمار دریافت و وارد می‌کند
4. بعد از تایید، پزشک به آخرین Chat Summary بیمار دسترسی پیدا می‌کند

#### API Endpoints:

##### 1.1 درخواست دسترسی
```
POST /crazyminer/patient/request/
Headers: Authorization: Bearer <doctor_token>
```
Body:
```json
{
    "patient_phone": "09123456789"
}
```
Response:
```json
{
    "request_id": "uuid-here",
    "message": "کد تایید به شماره بیمار ارسال شد",
    "patient_phone": "09123456789"
}
```

##### 1.2 تایید کد OTP
```
POST /crazyminer/patient/verify/
Headers: Authorization: Bearer <doctor_token>
```
Body:
```json
{
    "request_id": "uuid-here",
    "otp_code": "123456"
}
```
Response:
```json
{
    "success": true,
    "message": "دسترسی با موفقیت تایید شد",
    "access_token": "token-here",
    "expires_at": "2024-01-01T12:00:00Z"
}
```

##### 1.3 دریافت اطلاعات بیمار
```
GET /crazyminer/patient/data/
Headers: 
  - Authorization: Bearer <doctor_token>
  - X-Patient-Access-Token: <access_token>
```
Response:
```json
{
    "patient_phone": "09123456789",
    "patient_name": "نام بیمار",
    "latest_summary": {
        "id": "summary-id",
        "content": "محتوای خلاصه",
        "summary_text": "متن خلاصه شده",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:30:00Z"
    },
    "has_summary": true,
    "from_cache": false
}
```

### 2. پرداخت برای کاربران SOAPify

#### ویژگی‌ها:
- پزشک می‌تواند برای کاربران SOAPify پرداخت انجام دهد
- نیازی به ایجاد کاربر ساختگی نیست
- تراکنش با `is_soapify=true` مشخص می‌شود

#### API Endpoint:

```
POST /crazyminer/patient/soapify-payment/
Headers: Authorization: Bearer <doctor_token>
```
Body:
```json
{
    "amount": 500000,
    "soapify_user_id": "user-id-in-soapify",
    "description": "پرداخت هزینه ویزیت"
}
```
Response:
```json
{
    "transaction_id": "uuid-here",
    "payment_url": "https://api.medogram.ir/payment/gateway-123-get",
    "amount": 500000,
    "soapify_user_id": "user-id-in-soapify",
    "status": "processing"
}
```

### 3. شارژ کیف پول (عملکرد قبلی)

```
POST /crazyminer/payment/create/
Headers: Authorization: Bearer <token>
```
Body:
```json
{
    "amount": 100000,
    "description": "شارژ کیف پول"
}
```

## مدل‌های داده

### PatientAccessRequest
- ذخیره درخواست‌های دسترسی پزشک به اطلاعات بیمار
- مدیریت OTP و token دسترسی
- زمان انقضا: 24 ساعت برای access token

### PatientDataCache
- کش اطلاعات بیمار برای کاهش بار روی SOAPify
- زمان انقضا: 1 ساعت

### CrazyMinerPayment (به‌روزرسانی شده)
- فیلد `is_soapify`: تشخیص پرداخت‌های SOAPify
- فیلد `soapify_user_id`: شناسه کاربر در SOAPify

## تنظیمات

### 1. تنظیمات پایه
```python
# settings.py

# SOAPify Connection
SOAPIFY_API_URL = 'http://localhost:8000/api'  # یا آدرس واقعی
SOAPIFY_API_KEY = 'your-api-key'
SOAPIFY_USE_DIRECT_DB = True  # برای اتصال مستقیم به دیتابیس

# Payment Gateway
PAYMENT_GATEWAY_URL = 'https://api.medogram.ir'
PAYMENT_API_KEY = 'your-payment-api-key'
PAYMENT_REDIRECT_URL = 'https://your-domain.com/payment-redirect/'

# SMS (Kavenegar)
KAVEH_NEGAR_API_KEY = 'your-kavenegar-key'
```

### 2. تنظیم Template در کاوه‌نگار
باید template با نام `patient-access-otp` در پنل کاوه‌نگار ایجاد شود:
```
کد تایید دسترسی به اطلاعات پزشکی شما: %token%
این کد فقط 5 دقیقه اعتبار دارد.
```

## نصب و راه‌اندازی

### 1. نصب وابستگی‌ها
```bash
pip install cryptography kavenegar
```

### 2. اجرای migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. اتصال به SOAPify
اگر `SOAPIFY_USE_DIRECT_DB=True` است، باید به دیتابیس SOAPify دسترسی مستقیم داشته باشید.
در غیر این صورت، API endpoints زیر باید در SOAPify پیاده‌سازی شوند:
- `GET /api/users/by-phone/{phone}/`
- `GET /api/chat/summaries/latest/{user_id}/`

## امنیت

### 1. OTP
- کد 6 رقمی تصادفی
- انقضا بعد از 5 دقیقه
- حداکثر 3 بار تلاش

### 2. Access Token
- توکن 64 کاراکتری تصادفی
- انقضا بعد از 24 ساعت
- محدود به پزشک و بیمار خاص

### 3. Cache
- اطلاعات بیمار برای 1 ساعت کش می‌شود
- کاهش بار روی دیتابیس SOAPify

## نکات مهم

1. **دسترسی به دیتابیس**: CrazyMiner باید به دیتابیس SOAPify دسترسی داشته باشد
2. **کاربران**: فقط پزشکان در CrazyMiner ثبت‌نام می‌کنند
3. **پرداخت SOAPify**: تراکنش‌ها با `is_soapify=true` از تراکنش‌های عادی جدا می‌شوند
4. **موازی‌سازی**: می‌توان چندین درخواست دسترسی همزمان داشت

## مثال استفاده کامل

```python
import requests

# 1. درخواست دسترسی به بیمار
response = requests.post(
    'https://crazyminer.com/crazyminer/patient/request/',
    headers={'Authorization': 'Bearer doctor-token'},
    json={'patient_phone': '09123456789'}
)
request_id = response.json()['request_id']

# 2. دریافت کد از بیمار و تایید
otp_code = input("کد تایید را وارد کنید: ")
response = requests.post(
    'https://crazyminer.com/crazyminer/patient/verify/',
    headers={'Authorization': 'Bearer doctor-token'},
    json={'request_id': request_id, 'otp_code': otp_code}
)
access_token = response.json()['access_token']

# 3. دریافت اطلاعات بیمار
response = requests.get(
    'https://crazyminer.com/crazyminer/patient/data/',
    headers={
        'Authorization': 'Bearer doctor-token',
        'X-Patient-Access-Token': access_token
    }
)
patient_data = response.json()
```