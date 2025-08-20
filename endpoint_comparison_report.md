# گزارش مقایسه اند پوینت‌های SOAPify

## خلاصه بررسی
این گزارش مقایسه کاملی بین اند پوینت‌های تعریف شده در کد و مستندات ReDoc ارائه می‌دهد.

## مقایسه اند پوینت‌ها

### 1. Auth (احراز هویت)
✅ **تطابق کامل**
- کد: `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/token/verify/`
- ReDoc: همین موارد
- accounts: `/api/auth/login/`, `/api/auth/logout/`

### 2. Users/Accounts  
⚠️ **تفاوت در نام‌گذاری**
- کد: اند پوینت‌ها در `accounts` تعریف شده: `/api/users/`, `/api/users/<id>/`
- ReDoc: به عنوان `Users` مستند شده

### 3. Encounters
✅ **تطابق نسبی**
- کد: `/api/encounters/`, `/api/encounters/create/`, `/api/encounters/<id>/`
- کد: `/api/audio/presigned-url/`, `/api/audio/commit/`
- ReDoc: مطابقت دارد

### 4. STT (Speech to Text)
✅ **تطابق کامل**
- کد: `/api/stt/transcribe/`, `/api/stt/encounter/<id>/process/`, `/api/stt/transcript/<id>/`
- ReDoc: همین موارد

### 5. NLP
✅ **تطابق کامل**  
- کد: `/api/nlp/generate/<id>/`, `/api/nlp/drafts/<id>/`, `/api/nlp/drafts/<id>/update-section/`
- ReDoc: مطابقت دارد

### 6. Checklist
✅ **تطابق کامل با ViewSet**
- کد: استفاده از Router برای catalog, evaluations, templates
- ReDoc: `/api/checklist/catalog/`, `/api/checklist/evaluations/`, `/api/checklist/templates/`

### 7. Search
✅ **تطابق کامل**
- کد: `/api/search/`, `/api/search/suggestions/`, `/api/search/reindex/`, `/api/search/analytics/`
- ReDoc: مطابقت دارد

### 8. Integrations
✅ **تطابق کامل**
- کد: `/api/integrations/otp/send/`, `/api/integrations/patients/search/`, etc.
- ReDoc: مطابقت دارد

### 9. Outputs
✅ **تطابق کامل**
- کد: `/api/outputs/finalize/`, `/api/outputs/finalized/<id>/`, `/api/outputs/download/<id>/`
- ReDoc: مطابقت دارد

### 10. Analytics
✅ **تطابق کامل**
- کد: `/api/analytics/overview/`, `/api/analytics/users/`, `/api/analytics/performance/`
- ReDoc: مطابقت دارد

### 11. AdminPlus
⚠️ **مستندات ناقص در ReDoc**
- کد: `/adminplus/api/health/`, `/adminplus/api/tasks/`, etc.
- ReDoc: فقط برخی اند پوینت‌ها ذکر شده

### 12. Uploads
✅ **تطابق کامل**
- کد: `/api/uploads/session/create/`, `/api/uploads/chunk/`, `/api/uploads/commit/`
- ReDoc: مطابقت دارد

### 13. Embeddings
❌ **در ReDoc وجود ندارد**
- کد: `/api/embeddings/ping/`
- ReDoc: اصلاً ذکر نشده

## اند پوینت‌های اضافی در ReDoc که در کد نیستند
هیچ موردی یافت نشد - همه اند پوینت‌های ReDoc در کد وجود دارند.

## نتیجه‌گیری
1. اکثر اند پوینت‌ها به درستی پیاده‌سازی شده‌اند ✅
2. مستندات ReDoc نسبتاً کامل است
3. نیاز به اضافه کردن embeddings به ReDoc
4. نیاز به تکمیل مستندات adminplus
5. یکسان‌سازی نام‌گذاری accounts/users

## توصیه‌ها
1. مستندات embeddings را به ReDoc اضافه کنید
2. مستندات کامل adminplus را اضافه کنید  
3. API_DOCUMENTATION.md را با اطلاعات کامل ReDoc به‌روزرسانی کنید
4. PROJECT_SUMMARY.md را اصلاح کنید
