# telemedicine/signals.py
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.template.loader import render_to_string
from kavenegar import KavenegarAPI
from telemedicine.models import BoxMoney, Transaction, Visit, APKDownloadStat
from django.utils import timezone
from django.db.models import F



# ──────────────────────────────
# تنظیمات ثابت
# ──────────────────────────────
User = get_user_model()   # ← مدل کاربر فعلی پروژه
TOPUP_AMOUNT = 300000   # 


# ──────────────────────────────
# ۱) قبل از ذخیرهٔ کاربر
# ──────────────────────────────
@receiver(pre_save, sender=User)
def set_username_to_phone(sender, instance, **kwargs):
    """
    Ensure a User instance has a username by copying its phone_number when username is empty.
    
    When run (typically as a pre_save signal receiver for the User model), if the instance has no `username`
    and has a `phone_number` attribute with a truthy value, this mutates `instance.username` to the
    string form of `phone_number` before the instance is saved.
    """
    if not instance.username and getattr(instance, "phone_number", None):
        instance.username = str(instance.phone_number)


# ──────────────────────────────
# ۲) پس از ایجاد کاربر جدید
# ──────────────────────────────

@receiver(post_save, sender=User)
def init_wallet_and_send_welcome_sms(sender, instance, created, **kwargs):
    """
    Create a BoxMoney wallet for a newly created user with the configured TOPUP_AMOUNT.
    
    This receiver runs on User post-save and, only when `created` is True, creates a BoxMoney record for `instance` with amount equal to TOPUP_AMOUNT.
    
    Parameters:
        instance (User): The User instance that was saved.
        created (bool): True if the User was just created; handler does nothing when False.
    """
    if not created:  # فقط در اولین ایجاد
        return
    
    BoxMoney.objects.create(user=instance, amount=TOPUP_AMOUNT)



    
    


# ──────────────────────────────
# ۳) افزایش موجودی پس از تراکنش موفق
# ──────────────────────────────
@receiver(post_save, sender=Transaction)
def update_wallet_after_transaction(sender, instance, **kwargs):
    """
    Increment the user's BoxMoney wallet when a Transaction becomes successful.
    
    This signal handler (intended for Transaction post-save) checks the saved Transaction instance,
    and if its status is "successful" ensures a BoxMoney exists for the transaction's user and
    atomically increases the wallet's amount by the transaction's amount. If the status is not
    "successful", no change is made.
    """
    if instance.status != "successful":
        return

    wallet, _ = BoxMoney.objects.get_or_create(user=instance.user)
    BoxMoney.objects.filter(pk=wallet.pk).update(amount=F('amount') + instance.amount)


# ──────────────────────────────
# ۴) ایمیل جزئیات ویزیت
# ──────────────────────────────

@receiver(post_save, sender=Visit)
def send_visit_email(sender, instance, created, **kwargs):
    """
    Send an HTML email with visit details when a Visit is created.
    
    Renders the 'visit_email.html' template with the created Visit instance as context and sends the resulting HTML email (subject "Visit Details: <visit.name>") from info@medogram.ir to shabanimehran@gmail.com. This function is a Django post_save signal receiver and runs only when `created` is True.
    
    Parameters:
        sender: The model class sending the signal (ignored by this function).
        instance: The Visit instance that was created — used as the template context.
        created (bool): True if the instance was created (email is sent only in this case).
    """
    if created:
        html_content = render_to_string('visit_email.html', {'visit': instance})
        email = EmailMessage(
            subject=f"Visit Details: {instance.name}",
            body=html_content,
            from_email='info@medogram.ir',
            to=['shabanimehran@gmail.com'],
        )
        email.content_subtype = "html"
        email.send()


# ──────────────────────────────
# ۵) پیامک تأیید ایجاد ویزیت
# ──────────────────────────────
@receiver(post_save, sender=Visit)
def sms_visit_created(sender, instance, created, **kwargs):
    """
    Send a one-time verification SMS when a Visit is created.
    
    When a new Visit instance is created, if its related user has a phone_number, this handler requests Kavenegar to send a verification SMS using a random 6-digit token and the "register-visit" template. Failures contacting the SMS API are caught and logged (printed) but not re-raised.
    """
    if not created:
        return

    phone = getattr(instance.user, "phone_number", None)
    if phone:
        try:
            api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
            api.verify_lookup({
                "receptor": phone,
                "token": random.randint(100000, 999999),
                "template": "register-visit",
            })
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Kavenegar register-visit SMS failed: {exc}")

            
apk_downloaded = Signal()

@receiver(apk_downloaded)
def on_apk_downloaded(sender, **kwargs):
    # اگر ردیف وجود ندارد، بساز
    """
    Handle an APK download signal by ensuring a stat record exists and atomically recording the download.
    
    Ensures an APKDownloadStat row with key "helssa_apk" exists (creating it if missing), then atomically increments its `total` counter by 1 and sets `last_download_at` to the current time.
    
    Parameters:
        sender: The signal sender (unused).
    """
    APKDownloadStat.objects.get_or_create(key="helssa_apk")
    # افزایش اتمیک و ثبت زمان آخرین دانلود
    APKDownloadStat.objects.filter(key="helssa_apk").update(
        total=F('total') + 1,
        last_download_at=timezone.now()
    )
