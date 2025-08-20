# telemedicine/models.py
import time
from io import BytesIO

from PIL import Image
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import models
from pillow_heif import register_heif_opener
from rest_framework.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number=None, email=None, username=None, password=None, **extra_fields):
        """
        Create and persist a new user, requiring at least a phone number or an email.
        
        If username is not provided it will be derived from phone_number (preferred) or email.
        The password is hashed via set_password before saving.
        
        Parameters:
            phone_number (str | None): User's phone number. Required if email is omitted.
            email (str | None): User's email. Required if phone_number is omitted.
            username (str | None): Desired username; if omitted it is derived from phone_number or email.
            password (str | None): Plain-text password; will be hashed before storing.
            **extra_fields: Additional model fields forwarded to the user model.
        
        Returns:
            CustomUser: The created and saved user instance.
        
        Raises:
            ValueError: If both phone_number and email are not provided.
        """
        if not phone_number and not email:
            raise ValueError('شماره موبایل یا ایمیل ضروری است')

        if not username:
            username = phone_number if phone_number else email

        user = self.model(phone_number=phone_number, email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        """
        Create and save a superuser with staff and superuser privileges.
        
        Ensures `is_staff` and `is_superuser` are set to True, requires both `username` and `email`,
        and delegates creation to `create_user`.
        
        Parameters:
            username (str): Username for the superuser.
            email (str): Email address for the superuser.
            password (str): Plain-text password for the superuser.
            **extra_fields: Additional model fields forwarded to `create_user`.
        
        Returns:
            CustomUser: The created superuser instance.
        
        Raises:
            ValueError: If `email` or `username` is not provided (error messages are in Persian).
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not email:
            raise ValueError('برای سوپر یوزر، ایمیل ضروری است')
        if not username:
            raise ValueError('برای سوپر یوزر، یوزرنیم ضروری است')

        return self.create_user(username=username, email=email, password=password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    username = models.CharField(max_length=15, unique=True, null=True, blank=True)
    auth_code = models.IntegerField(unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    is_doctor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        """
        Return the user's username as the model's string representation.
        
        This provides a human-readable identifier for the user instance, suitable for admin displays and logging.
        """
        return self.username

    def has_perm(self, perm, obj=None):
        """
        Return whether the user has the given permission.
        
        This implementation grants all permissions only to superusers. The `perm`
        and `obj` arguments are accepted for compatibility with Django's auth
        API but are ignored.
        
        Parameters:
            perm (str): Permission codename (ignored).
            obj (optional): Object to check permission against (ignored).
        
        Returns:
            bool: True if the user is a superuser, otherwise False.
        """
        return self.is_superuser

    def has_module_perms(self, app_label):
        """
        Return whether the user has permissions for the given app.
        
        This implementation grants module-level permissions only to superusers.
        
        Parameters:
            app_label (str): The Django app label being checked (ignored by this implementation).
        
        Returns:
            bool: True if the user is a superuser, otherwise False.
        """
        return self.is_superuser

    def get_full_name(self):
        """
        Return the user's full name.
        
        Returns:
            str: The user's username (used as the full name).
        """
        return self.username

    def get_short_name(self):
        """
        Return the user's short display name.
        
        This returns the user's `username`, which is used as the short name shown in UIs.
        If `username` is unset, this will return None.
        """
        return self.username


def drug_image_path(instance, filename):
    """
    Return a deterministic upload path for a drug image.
    
    The path is built as 'drug_images/<user_id>/<unix_timestamp>_<filename>'. Requires that
    `instance` has a related `user` with an `id` attribute; `filename` is appended to the path.
    """
    return f'drug_images/{instance.user.id}/{int(time.time())}_{filename}'




# مدل Visit برای مدیریت اطلاعات ویزیت‌ها
class Visit(models.Model):
    URGENCY_CHOICES = [
        ('prescription', 'نسخه نویسی داروهای پر مصرف'),
        ('diet', 'رژیم درمانی'),
        ('addiction', 'ترک اعتیاد'),
        ('online_consultation', 'ویزیت و مشاوره آنلاین')
    ]

    GENERAL_SYMPTOMS = [
        ('fever', 'تب'),
        ('fatigue', 'خستگی'),
        ('weight_loss', 'کاهش وزن'),
        ('appetite_loss', 'کاهش اشتها'),
        ('night_sweats', 'تعریق شبانه'),
        ('general_pain', 'درد عمومی'),
        ('swollen_lymph_nodes', 'تورم غدد لنفاوی'),
        ('chills', 'لرز'),
        ('malaise', 'احساس ناخوشی عمومی')
    ]

    NEUROLOGICAL_CATEGORIES = [
        ('headache', 'سردرد'),
        ('dizziness', 'سرگیجه'),
        ('seizures', 'تشنج'),
        ('numbness', 'بی‌حسی'),
        ('weakness', 'ضعف عضلانی'),
        ('memory_loss', 'از دست دادن حافظه'),
        ('speech_difficulty', 'مشکل در تکلم'),
        ('vision_problems', 'مشکلات بینایی'),
        ('migraine', 'میگرن'),
        ('tremor', 'لرزش')
    ]

    CARDIOVASCULAR_CATEGORIES = [
        ('chest_pain', 'درد قفسه سینه'),
        ('palpitations', 'تپش قلب'),
        ('shortness_of_breath', 'تنگی نفس'),
        ('swelling', 'تورم'),
        ('high_blood_pressure', 'فشار خون بالا'),
        ('fatigue', 'خستگی'),
        ('fainting', 'غش کردن'),
        ('irregular_heartbeat', 'ضربان قلب نامنظم'),
        ('low_blood_pressure', 'فشار خون پایین')
    ]

    GASTROINTESTINAL_CATEGORIES = [
        ('nausea', 'حالت تهوع'),
        ('vomiting', 'استفراغ'),
        ('diarrhea', 'اسهال'),
        ('constipation', 'یبوست'),
        ('abdominal_pain', 'درد شکم'),
        ('bloating', 'نفخ'),
        ('heartburn', 'سوزش سر دل'),
        ('loss_of_appetite', 'بی‌اشتهایی'),
        ('indigestion', 'سوء هاضمه')
    ]

    RESPIRATORY_CATEGORIES = [
        ('cough', 'سرفه'),
        ('shortness_of_breath', 'تنگی نفس'),
        ('wheezing', 'خس خس سینه'),
        ('chest_tightness', 'سفتی قفسه سینه'),
        ('sore_throat', 'گلودرد'),
        ('runny_nose', 'آبریزش بینی'),
        ('fever', 'تب'),
        ('sneezing', 'عطسه'),
        ('difficulty_breathing', 'مشکل در تنفس')
    ]

    # فیلدهای مدل
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='visits')
    name = models.CharField(max_length=100)
    urgency = models.CharField(max_length=20)
    general_symptoms = models.CharField(max_length=50)
    neurological_symptoms = models.CharField(max_length=50, blank=True)
    cardiovascular_symptoms = models.CharField(max_length=50, blank=True)
    gastrointestinal_symptoms = models.CharField(max_length=50, blank=True)
    respiratory_symptoms = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    drug_images = models.ImageField(
        upload_to=drug_image_path,
        blank=True,
        null=True,
        verbose_name='تصاویر دارو'
    )

    def save(self, *args, **kwargs):
        """
        Convert raw bytes and HEIC/HEIF drug image uploads to storable image files before saving the Visit.
        
        If self.drug_images is raw bytes, converts it to a Django ContentFile. If the uploaded file has a
        '.heic' or '.heif' extension, attempts to convert it to a JPEG (RGB, quality=85) and replaces the
        stored file with the resulting JPEG. Conversion failures are caught and ignored so saving the model
        still completes.
        """
        # --- 1) اگر به صورت بایت خام آمده باشد، تبدیل به فایل می‌کنیم ---
        if isinstance(self.drug_images, bytes):
            # می‌توانید نام فایل را بسته به نیازتان تغییر دهید
            self.drug_images = ContentFile(self.drug_images, name='uploaded_image.jpg')

        # --- 2) اگر فایل آپلود شده پسوند HEIC/HEIF داشت، تبدیل به JPEG می‌کنیم ---
        if self.drug_images:
            file_name = self.drug_images.name.lower()
            # اگر بخواهید صرفاً براساس پسوند عمل کنید:
            if file_name.endswith(('.heic', '.heif')):
                try:
                    register_heif_opener()
                    img = Image.open(self.drug_images)
                    buffer = BytesIO()
                    img.convert('RGB').save(buffer, format='JPEG', quality=85)
                    buffer.seek(0)
                    new_name = file_name.rsplit('.', 1)[0] + '.jpg'
                    self.drug_images.save(new_name, ContentFile(buffer.getvalue()), save=False)
                except Exception as e:
                    # خطا در تبدیل فرمت از HEIC/HEIF؛ صرفاً رد می‌شویم تا عملیات سیو مختل نشود.
                    print(f"[WARN] تبدیل HEIC/HEIF به JPEG ناموفق بود: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        """
        Return a human-readable representation for the Visit instance.
        
        Returns:
            str: Representation in the format "<name> - <id>", combining the visit's name and its primary key.
        """
        return f"{self.name} - {self.id}"

    


class Transaction(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='transactions')
    trans_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.PositiveIntegerField()
    card_num = models.CharField(max_length=20, blank=True, null=True)  # شماره کارت
    factor_id = models.CharField(max_length=100, blank=True, null=True)  # شناسه فاکتور
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        Return a human-readable representation of the transaction.
        
        Returns:
            str: Formatted as "Transaction <user.phone_number> - <amount> - <status>".
        """
        return f"Transaction {self.user.phone_number} - {self.amount} - {self.status}"


def validate_image_url(value):
    """
    Validate that `value` is a syntactically valid URL that appears to reference a common image file.
    
    The function checks that `value` is a valid URL and that its path contains one of the supported image extensions: .jpg, .jpeg, .png, .gif, .webp. If validation fails, a django ValidationError is raised with the Persian message 'لطفاً یک آدرس URL معتبر وارد کنید'.
    
    Parameters:
        value (str): The URL to validate.
    
    Raises:
        django.core.exceptions.ValidationError: If `value` is not a valid URL or does not appear to reference a supported image file (message: 'لطفاً یک آدرس URL معتبر وارد کنید').
    """
    url_validator = URLValidator()
    try:
        url_validator(value)
        if not any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            raise ValidationError('لطفاً یک آدرس تصویر معتبر وارد کنید')
    except ValidationError:
        raise ValidationError('لطفاً یک آدرس URL معتبر وارد کنید')

class Blog(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    author = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='blogs')
    image1 = models.URLField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name='آدرس تصویر اول',
        validators=[validate_image_url],
        help_text='آدرس URL تصویر را وارد کنید (مثال: https://example.com/image.jpg)'
    )
    image2 = models.URLField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name='آدرس تصویر دوم',
        validators=[validate_image_url],
        help_text='آدرس URL تصویر را وارد کنید (مثال: https://example.com/image.jpg)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        Return the blog's title as its string representation.
        
        Returns:
            str: The blog post's title.
        """
        return self.title

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField(max_length=500, blank=True)  # حذف null=True
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="comments")  # رابطه ForeignKey به Blog
    likes = models.PositiveIntegerField(default=0)  # تعداد لایک‌ها
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """
        Return a short, human-readable representation of the comment.
        
        The string identifies the comment's author by username, e.g. "Comment by alice".
        """
        return f"Comment by {self.user.username}"

    def like(self):
        """
        Increment the comment's like count by one and persist the change.
        
        Increments the instance's `likes` field and saves the model to the database.
        """
        self.likes += 1
        self.save()


class BoxMoney(models.Model):
    """کیف پول کاربر برای خرید سرویس‌ها"""
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='box_money')
    amount = models.PositiveIntegerField(default=0)

    def has_sufficient_balance(self, price: int) -> bool:
        """
        Return True if the BoxMoney balance is at least the given price.
        
        Parameters:
            price (int): Amount to compare against the stored balance.
        
        Returns:
            bool: True when the current balance >= price, otherwise False.
        """
        return self.amount >= price

    def deduct_amount(self, price: int) -> bool:
        """
        Deduct the given amount from the wallet if sufficient balance exists.
        
        If the wallet has at least `price`, the amount is subtracted and the model is saved; otherwise no change is made.
        
        Parameters:
            price (int): Amount to deduct (in the same integer currency units stored on the model).
        
        Returns:
            bool: True when the deduction succeeded, False when the balance was insufficient.
        """
        if self.has_sufficient_balance(price):
            self.amount -= price
            self.save(update_fields=['amount'])
            return True
        return False

    def add_amount(self, amount: int) -> None:
        """
        Increase the user's wallet balance by the given amount using an atomic database update.
        
        This performs an atomic F-expression update on the BoxMoney row (by primary key) to add `amount` to the stored balance, avoiding a read-modify-write race. Passing a negative value will decrease the balance.
        """
        BoxMoney.objects.filter(pk=self.pk).update(amount=F('amount') + amount)

    def get_balance(self) -> int:
        """
        Return the current wallet balance.
        
        Returns:
            int: The user's current balance.
        """
        return self.amount

    def __str__(self):
        """
        Return a concise human-readable representation of the BoxMoney instance.
        
        The string includes the associated user's phone number and the current wallet amount in the format:
        "BoxMoney <phone_number> - <amount>".
        """
        return f"BoxMoney {self.user.phone_number} - {self.amount}"

class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    national_code = models.CharField(max_length=12)
    order_number = models.CharField(max_length=255, unique=True)
    disease_name = models.CharField(max_length=50, null=True, blank=True)
    download_url = models.URLField(max_length=200, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # ساخت خودکار مسیر دانلود
        """
        Ensure the Order has a download URL before saving.
        
        If download_url is empty, populate it with
        https://api.medogram.ir/order/download/order_{national_code}.pdf using the instance's national_code,
        then call the superclass save to persist the instance.
        """
        if not self.download_url:  # اگر مسیر دانلود خالی بود
            self.download_url = f"https://api.medogram.ir/order/download/order_{self.national_code}.pdf"
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Return a human-readable representation of the Order.
        
        Combines the order's first_name and last_name separated by a space.
        
        Returns:
            str: The order's full name in the format "First Last".
        """
        return f"{self.first_name} {self.last_name}"
    

class APKDownloadStat(models.Model):
    """
    شمارندهٔ دانلود فایل APK (Single-row / keyed).
    """
    key = models.CharField(max_length=50, unique=True, default="helssa_apk")
    total = models.PositiveBigIntegerField(default=0)
    last_download_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """
        Return a human-readable representation of the APKDownloadStat.
        
        Returns:
            str: A concise string in the format "<key> -> <total>" showing the stat key and its total count.
        """
        return f"{self.key} -> {self.total}"


class CrazyMinerPayment(models.Model):
    """مدل برای ذخیره تراکنش‌های پرداخت CrazyMiner"""
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('processing', 'در حال پردازش'),
        ('completed', 'تکمیل شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='crazyminer_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=0)  # مبلغ به ریال
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # فیلدهای مربوط به درگاه پرداخت
    gateway_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_reference_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_tracking_code = models.CharField(max_length=255, blank=True, null=True)
    
    # داده‌های رمزنگاری شده
    encrypted_user_data = models.TextField(blank=True, help_text="اطلاعات رمزنگاری شده کاربر")
    
    # توضیحات و URLs
    description = models.TextField(blank=True)
    callback_url = models.URLField(blank=True)
    redirect_url = models.URLField(blank=True)
    
    # زمان‌ها
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "پرداخت CrazyMiner"
        verbose_name_plural = "پرداخت‌های CrazyMiner"
    
    def __str__(self):
        return f"پرداخت {self.id} - {self.user.phone_number} - {self.amount} ریال - {self.get_status_display()}"
    
    def mark_completed(self):
        """تکمیل تراکنش"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self):
        """علامت‌گذاری به عنوان ناموفق"""
        self.status = 'failed'
        self.save()


class CrazyMinerPaymentLog(models.Model):
    """لاگ فعالیت‌های پرداخت"""
    
    LOG_TYPE_CHOICES = [
        ('request', 'درخواست پرداخت'),
        ('callback', 'بازگشت از درگاه'),
        ('verification', 'تایید پرداخت'),
        ('user_fetch', 'دریافت اطلاعات کاربر'),
        ('error', 'خطا'),
    ]
    
    payment = models.ForeignKey(
        CrazyMinerPayment, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    message = models.TextField()
    raw_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "لاگ پرداخت"
        verbose_name_plural = "لاگ‌های پرداخت"
    
    def __str__(self):
        return f"{self.get_log_type_display()} - {self.payment.id} - {self.created_at}"
