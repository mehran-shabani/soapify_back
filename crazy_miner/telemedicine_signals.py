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
    Set a User.username to the user's phone_number when username is empty.
    
    When used as a pre-save hook, if the User instance has no `username` and has a truthy
    `phone_number` attribute, this assigns `instance.username = str(instance.phone_number)`
    so the change is persisted when the instance is saved.
    """
    if not instance.username and getattr(instance, "phone_number", None):
        instance.username = str(instance.phone_number)


# ──────────────────────────────
# ۲) پس از ایجاد کاربر جدید
# ──────────────────────────────

@receiver(post_save, sender=User)
def init_wallet_and_send_welcome_sms(sender, instance, created, **kwargs):
    """
    Create an initial BoxMoney wallet for a newly created User.
    
    Runs on the User post-save signal. If `created` is True, creates a BoxMoney record
    linked to `instance` with amount set to TOPUP_AMOUNT. Does nothing when `created` is False.
    Note: despite the function name, this implementation only creates the wallet and does not send an SMS.
    
    Parameters:
        instance (User): The User instance that was saved.
        created (bool): True when the User was newly created; handler is a no-op otherwise.
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
    Record an APK download by ensuring a stat row exists and atomically updating its counters.
    
    Ensures an APKDownloadStat with key "helssa_apk" exists (creating it if missing), then atomically increments its `total` by 1 and sets `last_download_at` to the current time.
    """
    APKDownloadStat.objects.get_or_create(key="helssa_apk")
    # افزایش اتمیک و ثبت زمان آخرین دانلود
    APKDownloadStat.objects.filter(key="helssa_apk").update(
        total=F('total') + 1,
        last_download_at=timezone.now()
    )
