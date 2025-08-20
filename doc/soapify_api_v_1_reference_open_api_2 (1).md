# SOAPify API — Official Reference (v1)

**Spec source:** OpenAPI 2.0 (Swagger) — internal build.\
**Base URL (dev):** `http://127.0.0.1:8000/`\
**Consumes / Produces:** `application/json`\
**Auth:** Basic (dev) و JWT Bearer (پیشنهادی برای کلاینت‌ها)

---

## فهرست مطالب

- مقدمه و اصول کلی
- احراز هویت و امنیت
- الگوهای پاسخ، وضعیت‌ها و صفحه‌بندی
- گروه‌ها و اندپوینت‌ها
  - AdminPlus
  - Analytics
  - Auth
  - STT و Audio
  - Uploads
  - Encounters
  - NLP (Drafts & Checklist)
  - Checklist (Catalog / Templates / Evaluations)
  - Search
  - Integrations (Helssa & Sessions)
  - Outputs (Finalization & Files & Sharing)
  - Users
- اشیای داده (Schemas)
- نمونه‌های درخواست/پاسخ
- تغییرات آینده و نکات اجرایی

---

## مقدمه و اصول کلی

SOAPify یک سرویس استخراج، تدوین و نهایی‌سازی یادداشت‌های پزشکی **SOAP** از ورودی‌های صوتی/متنی جلسه پزشک–بیمار است. این API لایه‌های آپلود صوت، رونویسی (STT)، تولید پیش‌نویس، چک‌لیست پویای ارزیابی، جستجو، یکپارچه‌سازی با Helssa و نهایی‌سازی خروجی را فراهم می‌کند.

- همه درخواست‌ها و پاسخ‌ها JSON هستند مگر خلاف آن (برای آپلود chunk).
- **زمان‌ها** در ISO 8601 و **UTC** ذخیره می‌شوند (مگر خلاف آن در فیلدها/مستندات ذکر شود).
- **Idempotency** در عملیات بازپردازش/ایندکس مجدد رعایت شود (کلاینت‌ها می‌توانند از توکن‌های تکرارپذیری خود استفاده کنند).

---

## احراز هویت و امنیت

### 1) Basic Auth

برای محیط توسعه و تست پنل ادمین. در هدر:

```
Authorization: Basic base64(username:password)
```

### 2) JWT (پیشنهادی)

#### دریافت توکن جفت (Access/Refresh)

`POST /api/auth/token/`

```json
{
  "username": "doctor01",
  "password": "******"
}
```

**پاسخ:**

```json
{
  "access": "<JWT>",
  "refresh": "<JWT>"
}
```

#### رفرش اکسس توکن

`POST /api/auth/token/refresh/`

```json
{ "refresh": "<refresh-token>" }
```

#### وریفای توکن

`POST /api/auth/token/verify/`

```json
{ "token": "<any-token>" }
```

#### استفاده در درخواست‌ها

```
Authorization: Bearer <access-token>
```

> نکته: برخی اندپوینت‌ها در spec با Basic مشخص شده‌اند؛ برای کلاینت‌های محصولی **حتماً** از JWT استفاده کنید.

---

## الگوهای پاسخ، وضعیت‌ها و صفحه‌بندی

- وضعیت‌های رایج:
  - `200 OK` برای خواندن/فهرست.
  - `201 Created` برای عملیات آغاز پردازش/ایجاد.
  - `204 No Content` برای حذف.
  - `400/401/403/404/422/429/5xx` برای خطاها.
- صفحه‌بندی استاندارد DRF:

```json
{
  "count": 123,
  "next": "<url or null>",
  "previous": "<url or null>",
  "results": [ ... ]
}
```

- هدرهای کلیدی:
  - `Authorization`
  - `Content-Type: application/json`

---

## AdminPlus

مدیریت سلامت سیستم، لاگ‌ها و وظایف (Celery/پس‌زمینه).

### GET `/adminplus/api/health/` — وضعیت سلامت سیستم

**200** نمونه پاسخ: `{ "status": "ok", ... }`

### GET `/adminplus/api/logs/` — لاگ عملیات

**200**: آرایه‌ای از رخدادها.

### GET `/adminplus/api/tasks/` — پایش تسک‌ها

**200**: وضعیت تسک‌های جاری/گذشته.

### GET `/adminplus/api/tasks/stats/` — آمار اجرا

**200**: شمارش و زمان‌بندی‌ها.

### POST `/adminplus/api/tasks/cancel/` — لغو تسک در حال اجرا

**201**: نتیجه لغو.

### POST `/adminplus/api/tasks/retry/` — تلاش مجدد برای تسک ناموفق

**201**: نتیجه برنامه‌ریزی تکرار.

### POST `/adminplus/api/export/` — برون‌بری داده‌های سامانه

**201**: لینک/مرجع خروجی.

---

## Analytics

### GET `/api/analytics/overview/` — نمای کلی شاخص‌ها

### GET `/api/analytics/performance/` — کارایی API

پارامترهای Query: `days` (پیش‌فرض 7)

### GET `/api/analytics/users/` — آنالیتیکس کاربران

Query: `user_id`, `days` (پیش‌فرض 30)

### GET `/api/analytics/alerts/` — هشدارهای فعال

### POST `/api/analytics/alerts/check/` — بررسی دستی قوانین هشدار

### POST `/api/analytics/alerts/{alert_id}/acknowledge/` — تأیید هشدار

Path: `alert_id`

### POST `/api/analytics/metric/` — ثبت متریک سفارشی

Body:

```json
{
  "name": "queue_depth",
  "value": 42,
  "metric_type": "gauge",
  "tags": {"queue": "stt"}
}
```

### POST `/api/analytics/activity/` — ثبت فعالیت کاربر

Body: `action` (الزامی), `resource`, `resource_id`, `metadata`

### POST `/api/analytics/business-metrics/` — محاسبه شاخص‌های بیزینسی

Body: `date_from`, `date_to` (YYYY-MM-DD)

---

## Auth

### POST `/api/auth/login/` — ورود و دریافت توکن

### POST `/api/auth/logout/` — خروج و ابطال توکن

### POST `/api/auth/token/` — دریافت جفت توکن (SimpleJWT)

### POST `/api/auth/token/refresh/` — رفرش اکسس

### POST `/api/auth/token/verify/` — وریفای

اسکیماها: **TokenObtainPair**, **TokenRefresh**, **TokenVerify** (بخش Schemas).

---

## STT و Audio

### POST `/api/audio/presigned-url/` — پری‌ساین برای آپلود صوت به S3

### POST `/api/audio/commit/` — ثبت نهایی فایل صوتی آپلود شده

### POST `/api/stt/transcribe/` — رونویسی یک قطعه صوت

### GET `/api/stt/transcript/{audio_chunk_id}/` — دریافت سگمنت‌های متن برای قطعه

Path: `audio_chunk_id`

### PUT `/api/stt/transcript/{segment_id}/` — ویرایش دستی متن سگمنت

Path: `segment_id`

### POST `/api/stt/encounter/{encounter_id}/process/` — آغاز STT برای همه قطعات جلسه

Path: `encounter_id`

### GET `/api/stt/encounter/{encounter_id}/transcript/` — متن کامل جلسه

Path: `encounter_id`

### GET `/api/stt/search/` — جستجوی متن رونویسی

Query: `q`, ...

---

## Uploads

جریان آپلود قطعه‌ای یا S3 direct-upload.

### POST `/api/uploads/session/create/` — ایجاد نشست آپلود

### POST `/api/uploads/chunk/` — آپلود chunk (multipart/form-data)

### POST `/api/uploads/commit/` — نهایی‌سازی نشست آپلود

### GET `/api/uploads/final/{session_id}/` — خروجی نهایی نشست

Path: `session_id`

### POST `/api/uploads/s3/presign/` — پری‌ساین S3

### POST `/api/uploads/s3/confirm/` — تأیید آپلود S3

---

## Encounters

### GET `/api/encounters/` — فهرست Encounterهای کاربر

### POST `/api/encounters/create/` — ایجاد Encounter جدید

### GET `/api/encounters/{encounter_id}/` — جزئیات Encounter با قطعات صوت

Path: `encounter_id`

---

## NLP (Drafts & Checklist)

### POST `/api/nlp/generate/{encounter_id}/` — آغاز استخراج SOAP برای Encounter

Path: `encounter_id`

### GET `/api/nlp/drafts/{encounter_id}/` — دریافت پیش‌نویس SOAP

### PUT `/api/nlp/drafts/{encounter_id}/update-section/` — بروزرسانی بخشی از پیش‌نویس

Path: `encounter_id`

### GET `/api/nlp/drafts/{encounter_id}/checklist/` — دریافت چک‌لیست پویا

### PUT `/api/nlp/drafts/{encounter_id}/checklist/{item_id}/` — بروزرسانی وضعیت آیتم چک‌لیست

Path: `encounter_id`, `item_id`

---

## Checklist (Catalog / Templates / Evaluations)

### Catalog

- **GET/POST** `/api/checklist/catalog/` — فهرست/ایجاد آیتم‌های کاتالوگ\
  Query: `page`
- **GET/PUT/PATCH/DELETE** `/api/checklist/catalog/{id}/`

**ChecklistCatalog** فیلدهای کلیدی: `title`, `description`, `category` (`subjective|objective|assessment|plan|general`), `priority` (`low|medium|high|critical`), `keywords` (object), `question_template`, `is_active`.

### Templates

- **GET/POST** `/api/checklist/templates/`
- **GET/PUT/PATCH/DELETE** `/api/checklist/templates/{id}/`
- **GET** `/api/checklist/templates/{id}/catalog_items/` — آیتم‌های کاتالوگ مرتبط با تمپلیت

**ChecklistTemplate**: `name`, `description`, `specialty`, `is_default`, `catalog_items_count` (readOnly).

### Evaluations

- **GET/POST** `/api/checklist/evaluations/`
- **GET/PUT/PATCH/DELETE** `/api/checklist/evaluations/{id}/`
- **POST** `/api/checklist/evaluations/evaluate_encounter/` — تریگر ارزیابی برای یک Encounter
- **GET** `/api/checklist/evaluations/summary/` — خلاصه وضعیت چک‌لیست برای Encounter

**ChecklistEval**: `encounter`, `catalog_item_id`, `status` (`covered|missing|partial|unclear`), `confidence_score`, `evidence_text`, `anchor_positions`, `generated_question`, `notes`.

---

## Search

### GET `/api/search/` — جستجوی هیبریدی

Query:

- `q` (ضروری)
- `encounter_id`
- `content_type` (`transcript|soap|checklist|notes`)
- `date_from`, `date_to` (`YYYY-MM-DD`)
- `page`, `page_size` (پیش‌فرض 20)

### GET `/api/search/suggestions/` — پیشنهادات بر اساس پیشوند

Query: `q`, `limit` (پیش‌فرض 10)

### GET `/api/search/analytics/` — آنالیز جستجو

Query: `days` (پیش‌فرض 30)

### POST `/api/search/reindex/` — بازایندکس محتوا برای یک Encounter

Body:

```json
{ "encounter_id": "<id>" }
```

---

## Integrations (Helssa & Sessions)

### GET `/api/integrations/health/` — سلامت یکپارچه‌سازی‌ها

### POST `/api/integrations/logout/` — خروج و لغو JWT window

### POST `/api/integrations/otp/send/` — ارسال OTP

### POST `/api/integrations/otp/verify/` — تأیید OTP و ایجاد JWT window

### GET `/api/integrations/session/status/` — وضعیت نشست و زمان باقیمانده

### POST `/api/integrations/session/extend/` — تمدید نشست

### Helssa Patients (Read-only)

- **GET** `/api/integrations/patients/search/` — جستجوی بیماران
- **GET** `/api/integrations/patients/{patient_ref}/info/` — اطلاعات پایه (بدون PHI)
- **POST** `/api/integrations/patients/{patient_ref}/access/` — درخواست دسترسی

---

## Outputs (Finalization & Files & Sharing)

### POST `/api/outputs/finalize/` — آغاز فرآیند نهایی‌سازی SOAP

### GET `/api/outputs/finalized/{encounter_id}/` — دریافت SOAP نهایی

Path: `encounter_id`

### GET `/api/outputs/files/{encounter_id}/` — لیست فایل‌های خروجی مرتبط

### POST `/api/outputs/download/{file_id}/` — تولید لینک دانلود پری‌ساین

### GET `/api/outputs/access/{link_id}/` — دسترسی عمومی بیمار به یادداشت (بدون ورود)

### POST `/api/outputs/link-patient/` — ایجاد لینک اشتراک با بیمار

---

## Users

### GET/POST `/api/users/` — فهرست/ایجاد کاربر

Query: `page`

### GET/PUT/PATCH `/api/users/{id}/` — دریافت/به‌روزرسانی جزئی/کامل

Path: `id`

**UserCreate**: `username*`, `password*`, `email`, `first_name`, `last_name`, `role` (`doctor|admin`), `phone_number`\
**User**: `id`, `username*`, `email`, `first_name`, `last_name`, `role`, `phone_number`, `updated_at`

---

## اشیای داده (Schemas)

### TokenObtainPair

```json
{
  "username": "string",
  "password": "string"
}
```

### TokenRefresh

```json
{
  "refresh": "string",
  "access": "string (readOnly)"
}
```

### TokenVerify

```json
{ "token": "string" }
```

### ChecklistCatalog

```json
{
  "id": 1,
  "title": "string",
  "description": "string",
  "category": "subjective|objective|assessment|plan|general",
  "priority": "low|medium|high|critical",
  "keywords": {"synonyms": ["fever", "pyrexia"]},
  "question_template": "string",
  "is_active": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### ChecklistTemplate

```json
{
  "id": 10,
  "name": "General Internal Medicine",
  "description": "...",
  "specialty": "IM",
  "is_default": false,
  "catalog_items_count": "42",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### ChecklistEval

```json
{
  "id": 55,
  "encounter": 123,
  "catalog_item": { /* ChecklistCatalog */ },
  "catalog_item_id": 1,
  "status": "covered|missing|partial|unclear",
  "confidence_score": 0.92,
  "evidence_text": "...",
  "anchor_positions": {"start": 120, "end": 164},
  "generated_question": "...",
  "notes": "...",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### User / UserCreate

```json
{
  "id": 7,
  "username": "doctor01",
  "email": "doc@example.com",
  "first_name": "Maryam",
  "last_name": "N.",
  "role": "doctor|admin",
  "phone_number": "+98...",
  "updated_at": "datetime"
}
```

---

## نمونه‌های درخواست/پاسخ

### نمونهٔ `curl` — ایجاد Encounter و آغاز پردازش

```bash
# 1) ورود و دریافت توکن
curl -s -X POST \
  http://127.0.0.1:8000/api/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"doctor01","password":"******"}'

# فرض کنید ACCESS در متغیر ذخیره شد
export TOKEN="<ACCESS>"

# 2) ایجاد Encounter جدید
curl -X POST \
  http://127.0.0.1:8000/api/encounters/create/ \
  -H 'Authorization: Bearer '"$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"patient_ref":"HS-12345","context":"OPD"}'

# 3) آغاز STT برای Encounter
curl -X POST \
  http://127.0.0.1:8000/api/stt/encounter/ENC123/process/ \
  -H 'Authorization: Bearer '"$TOKEN"

# 4) تولید پیش‌نویس SOAP
curl -X POST \
  http://127.0.0.1:8000/api/nlp/generate/ENC123/ \
  -H 'Authorization: Bearer '"$TOKEN"

# 5) دریافت پیش‌نویس
curl -X GET \
  http://127.0.0.1:8000/api/nlp/drafts/ENC123/ \
  -H 'Authorization: Bearer '"$TOKEN"

# 6) نهایی‌سازی خروجی
curl -X POST \
  http://127.0.0.1:8000/api/outputs/finalize/ \
  -H 'Authorization: Bearer '"$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"encounter_id":"ENC123"}'

# 7) دریافت SOAP نهایی
curl -X GET \
  http://127.0.0.1:8000/api/outputs/finalized/ENC123/ \
  -H 'Authorization: Bearer '"$TOKEN"
```

### نمونهٔ جستجو

```bash
curl -G http://127.0.0.1:8000/api/search/ \
  -H 'Authorization: Bearer '"$TOKEN" \
  --data-urlencode 'q=chest pain' \
  --data-urlencode 'content_type=transcript' \
  --data-urlencode 'page_size=20'
```

### نمونهٔ چک‌لیست

```bash
# افزودن آیتم کاتالوگ
curl -X POST http://127.0.0.1:8000/api/checklist/catalog/ \
  -H 'Authorization: Bearer '"$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Allergy history",
    "description":"Ask about known drug/food allergies",
    "category":"subjective",
    "priority":"high",
    "keywords": {"any": ["allergy","rash"]},
    "question_template":"Do you have any known allergies?",
    "is_active": true
  }'

# ارزیابی یک Encounter
curl -X POST http://127.0.0.1:8000/api/checklist/evaluations/evaluate_encounter/ \
  -H 'Authorization: Bearer '"$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"encounter":123}'
```

---

## نکات اجرایی و Best Practices

- برای پردازش‌های طولانی (STT/NLP/Finalize) **polling** سبک یا **webhook** (در آینده) را پیش‌بینی کنید.
- در به‌روزرسانی بخش‌های SOAP از اندپوینت سکشن‌محور استفاده کنید تا تعارض ویرایشی کاهش یابد.
- برای سشن‌های اشتراکی بیمار، لینک‌ها را کوتاه‌مدت و پری‌ساین نگه دارید.
- در جستجو از فیلتر `encounter_id` و تاریخ‌ها استفاده کنید تا latency کاهش یابد.

---

## تغییرات آینده (Roadmap کوتاه)

- افزودن وب‌هوک‌های رخداد (transcription.completed, draft.ready, finalize.completed)
- پشتیبانی از فیلدهای FHIR برای تبادل‌پذیری
- Rate limiting و کوتا (پروفایل‌محور)

---

### Contact

پشتیبانی: [**support@soapify.**](mailto\:support@soapify.app)**ir**\
License: **Proprietary**

