# 🎉 SOAPify Full Stack - Ready for Testing!

سیستم کامل مستندسازی پزشکی با هوش مصنوعی - شامل بک‌اند Django و فرانت‌اند React

## 🚀 راه‌اندازی سریع

### پیش‌نیازها

- Docker و Docker Compose
- 8GB RAM (توصیه شده)
- 10GB فضای خالی

### اجرای کامل سیستم

```bash
# 1. کلون پروژه (اگر قبلاً انجام نداده‌اید)
git clone <repository-url>
cd soapify_back

# 2. راه‌اندازی خودکار (تمام سرویس‌ها)
./start-full-stack.sh
```

### دسترسی به سیستم

پس از اجرای موفق، سرویس‌ها در آدرس‌های زیر در دسترس هستند:

- 🖥️ **فرانت‌اند React**: http://localhost:3000
- 🔗 **بک‌اند API**: http://localhost:8000  
- 📚 **مستندات API (Swagger)**: http://localhost:8000/swagger/
- 📖 **مستندات API (ReDoc)**: http://localhost:8000/redoc/
- 👤 **پنل ادمین Django**: http://localhost:8000/admin/
- 📊 **پنل مدیریت پیشرفته**: http://localhost:8000/adminplus/

### اطلاعات ورود پیش‌فرض

```
نام کاربری: admin
رمز عبور: admin
```

## 🏗️ معماری سیستم

```
┌─────────────────┐    ┌─────────────────┐
│   React App     │    │  Django API     │
│   (Port 3000)   │◄──►│  (Port 8000)    │
└─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │     Redis       │
                    │  Celery Worker  │
                    └─────────────────┘
```

## 📱 ویژگی‌های فرانت‌اند

### صفحات اصلی
- **داشبورد**: نمای کلی سیستم و آمار
- **مدیریت جلسات**: ایجاد و مشاهده جلسات پزشکی
- **رونویسی صوت**: تبدیل فایل‌های صوتی به متن
- **تولید SOAP**: تولید خودکار یادداشت‌های پزشکی
- **چک‌لیست**: بررسی کامل بودن مستندات
- **مدیریت خروجی‌ها**: دانلود و اشتراک گزارش‌ها
- **آنالیتیک**: گزارشات عملکرد سیستم

### ویژگی‌های فنی
- ✅ **رابط کاربری مدرن**: Tailwind CSS + React
- ✅ **RTL Support**: پشتیبانی کامل فارسی
- ✅ **احراز هویت امن**: JWT Authentication
- ✅ **Responsive Design**: سازگار با موبایل
- ✅ **Real-time Updates**: بروزرسانی لحظه‌ای
- ✅ **Error Handling**: مدیریت هوشمند خطاها

## 🔧 بک‌اند Django

### ماژول‌های پیاده‌سازی شده
- **accounts**: مدیریت کاربران و احراز هویت
- **encounters**: مدیریت جلسات پزشکی
- **stt**: رونویسی صوت با Whisper
- **nlp**: تولید SOAP با GPT
- **outputs**: تولید گزارش‌های نهایی
- **checklist**: سیستم چک‌لیست هوشمند
- **analytics**: آنالیتیک و گزارشات
- **integrations**: اتصال به سرویس‌های خارجی

## 🧪 تست سیستم

### مراحل تست کامل

1. **ورود به سیستم**
   - برو به http://localhost:3000
   - وارد شو با admin/admin

2. **ایجاد جلسه جدید**
   - از داشبورد روی "جلسه جدید" کلیک کن
   - اطلاعات بیمار را وارد کن

3. **آپلود فایل صوتی** (شبیه‌سازی)
   - وارد جزئیات جلسه شو
   - در آینده قابلیت آپلود اضافه خواهد شد

4. **تست رونویسی**
   - از بخش STT روی "شروع رونویسی" کلیک کن
   - (در حالت تست، داده‌های نمونه نمایش داده می‌شود)

5. **تولید SOAP**
   - از بخش NLP روی "تولید SOAP" کلیک کن
   - نتایج را مشاهده کن

6. **مشاهده آنالیتیک**
   - بخش آنالیتیک را بررسی کن
   - آمار سیستم را مشاهده کن

## 🐳 مدیریت Docker

### کامندهای مفید

```bash
# مشاهده وضعیت سرویس‌ها
docker-compose -f docker-compose.full.yml ps

# مشاهده لاگ‌ها
docker-compose -f docker-compose.full.yml logs -f

# ری‌استارت سرویس خاص
docker-compose -f docker-compose.full.yml restart backend

# توقف کامل سیستم
docker-compose -f docker-compose.full.yml down

# پاک‌سازی کامل (حذف volumes)
docker-compose -f docker-compose.full.yml down -v
```

### مانیتورینگ سرویس‌ها

```bash
# بررسی health check
docker-compose -f docker-compose.full.yml exec backend curl http://localhost:8000/healthz/

# اتصال به پایگاه داده
docker-compose -f docker-compose.full.yml exec db psql -U soapify -d soapify

# مشاهده وضعیت Celery
docker-compose -f docker-compose.full.yml exec backend celery -A soapify inspect active
```

## 🔧 تنظیمات پیشرفته

### متغیرهای محیطی

فایل `.env` را ویرایش کنید:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=soapify
POSTGRES_USER=soapify
POSTGRES_PASSWORD=your-secure-password

# AI Services (برای تست واقعی)
OPENAI_API_KEY=your-actual-openai-key

# External Services
CRAZY_MINER_API_KEY=your-sms-service-key
HELSSA_API_KEY=your-helssa-key
```

### تنظیم برای Production

1. `DEBUG=False` تنظیم کنید
2. `SECRET_KEY` قوی انتخاب کنید
3. پسوردهای پایگاه داده را تغییر دهید
4. SSL certificate اضافه کنید
5. کلیدهای واقعی AI services را وارد کنید

## 🚨 عیب‌یابی

### مشکلات رایج

**1. خطای اتصال به پایگاه داده**
```bash
# بررسی وضعیت PostgreSQL
docker-compose -f docker-compose.full.yml logs db
```

**2. مشکل فرانت‌اند**
```bash
# بررسی لاگ‌های React
docker-compose -f docker-compose.full.yml logs frontend
```

**3. خطای 502 Bad Gateway**
```bash
# بررسی وضعیت بک‌اند
docker-compose -f docker-compose.full.yml logs backend nginx
```

**4. مشکل Celery Worker**
```bash
# ری‌استارت worker
docker-compose -f docker-compose.full.yml restart celery-worker
```

### لاگ‌های مفید

```bash
# همه لاگ‌ها
docker-compose -f docker-compose.full.yml logs -f --tail=100

# فقط خطاها
docker-compose -f docker-compose.full.yml logs -f | grep -i error

# لاگ سرویس خاص
docker-compose -f docker-compose.full.yml logs -f backend
```

## 📊 عملکرد

### منابع مورد نیاز

- **RAM**: حداقل 4GB، توصیه 8GB
- **CPU**: 2 cores minimum
- **Storage**: 10GB برای development
- **Network**: پورت‌های 80, 3000, 8000

### بهینه‌سازی

```bash
# افزایش Celery workers
docker-compose -f docker-compose.full.yml up -d --scale celery-worker=3

# مانیتورینگ منابع
docker stats
```

## 🔄 بروزرسانی

### بروزرسانی کد

```bash
# دریافت تغییرات
git pull origin main

# rebuild و restart
docker-compose -f docker-compose.full.yml up --build -d
```

### مایگریشن پایگاه داده

```bash
# اجرای migrations
docker-compose -f docker-compose.full.yml exec backend python manage.py migrate
```

## 📞 پشتیبانی

### لینک‌های مفید

- 📚 **مستندات API**: http://localhost:8000/swagger/
- 🔗 **ReDoc**: http://localhost:8000/redoc/
- 👥 **GitHub Issues**: برای گزارش مشکلات
- 📧 **Email**: support@soapify.app

### گزارش مشکلات

هنگام گزارش مشکل، لطفاً اطلاعات زیر را ارائه دهید:

1. نسخه Docker و Docker Compose
2. سیستم عامل
3. لاگ‌های خطا
4. مراحل بازتولید مشکل

## 🎉 نتیجه‌گیری

**SOAPify Full Stack** یک سیستم کامل و آماده برای تست است که شامل:

- ✅ فرانت‌اند React مدرن و کاربرپسند
- ✅ بک‌اند Django قدرتمند با API کامل
- ✅ پایگاه داده PostgreSQL
- ✅ سیستم صف Celery + Redis
- ✅ تنظیمات Docker کامل
- ✅ مستندات جامع

**آماده تست و استفاده است!** 🚀

---

**تیم توسعه SOAPify**  
*"تبدیل مستندسازی پزشکی با هوش مصنوعی"* 🏥🤖