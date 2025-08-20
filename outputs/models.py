"""
Models for output generation and patient linking.
"""

from django.db import models
from django.contrib.auth import get_user_model
from encounters.models import Encounter
from nlp.models import SOAPDraft
import uuid

User = get_user_model()


class FinalizedSOAP(models.Model):
    """
    Finalized SOAP note ready for export.
    """
    STATUS_CHOICES = [
        ('finalizing', 'Finalizing'),
        ('finalized', 'Finalized'),
        ('exported', 'Exported'),
        ('error', 'Error'),
    ]
    
    soap_draft = models.OneToOneField(
        SOAPDraft,
        on_delete=models.CASCADE,
        related_name='finalized_soap'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='finalizing')
    finalized_data = models.JSONField(default=dict, help_text="Final SOAP data after GPT-4o processing")
    markdown_content = models.TextField(blank=True, help_text="Generated Markdown content")
    pdf_file_path = models.CharField(max_length=500, blank=True, help_text="S3 path to PDF file")
    json_file_path = models.CharField(max_length=500, blank=True, help_text="S3 path to JSON file")
    
    # Finalization metadata
    finalized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    finalization_model = models.CharField(max_length=50, default='gpt-4o')
    finalization_version = models.CharField(max_length=20, default='v1.0')
    quality_score = models.FloatField(null=True, blank=True, help_text="Final quality assessment")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'finalized_soaps'
        indexes = [
            models.Index(fields=['soap_draft']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Finalized SOAP for {self.soap_draft.encounter}"
    
    @property
    def encounter(self):
        return self.soap_draft.encounter
    
    @property
    def patient_ref(self):
        return self.soap_draft.encounter.patient_ref


class OutputFormat(models.Model):
    """Configuration for available output formats (PDF, JSON, etc.)."""
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('json', 'JSON'),
        ('markdown', 'Markdown'),
        ('html', 'HTML'),
        ('docx', 'DOCX'),
    ]

    name = models.CharField(max_length=100)
    format_type = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    template_name = models.CharField(max_length=200, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} ({self.format_type})"


class PatientInfo(models.Model):
    """Basic patient info linked to an encounter (no PHI beyond minimal identifiers)."""
    encounter = models.OneToOneField(Encounter, on_delete=models.CASCADE, related_name='patient_info')
    patient_id = models.CharField(max_length=100)
    patient_name = models.CharField(max_length=200)
    date_of_birth = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    additional_info = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.patient_name} ({self.patient_id})"


class ReportTemplate(models.Model):
    """Templates for generating reports in various formats."""
    name = models.CharField(max_length=150)
    template_type = models.CharField(max_length=50)
    template_content = models.TextField(blank=True)
    variables = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class GeneratedReport(models.Model):
    """Generated report artifact tied to a FinalizedSOAP and an OutputFormat."""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    finalized_soap = models.ForeignKey(FinalizedSOAP, on_delete=models.CASCADE, related_name='generated_reports')
    output_format = models.ForeignKey(OutputFormat, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['finalized_soap', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"Report for {self.finalized_soap} - {self.output_format.format_type}"

class PatientLink(models.Model):
    """
    Patient links for sharing finalized SOAP notes.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('direct', 'Direct Link'),
    ]
    
    finalized_soap = models.ForeignKey(
        FinalizedSOAP,
        on_delete=models.CASCADE,
        related_name='patient_links'
    )
    
    # Link details
    link_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    access_token = models.CharField(max_length=255, unique=True)
    
    # Patient contact info (no PHI stored)
    patient_phone = models.CharField(max_length=15, blank=True, help_text="For SMS delivery")
    patient_email = models.EmailField(blank=True, help_text="For email delivery")
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='sms')
    
    # Link management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField(help_text="Link expiration time")
    max_views = models.IntegerField(default=5, help_text="Maximum number of views allowed")
    view_count = models.IntegerField(default=0)
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    first_viewed_at = models.DateTimeField(null=True, blank=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_links'
        indexes = [
            models.Index(fields=['link_id']),
            models.Index(fields=['access_token']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Patient Link for {self.finalized_soap.patient_ref}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def is_accessible(self):
        return (
            self.status in ['sent', 'viewed'] and
            not self.is_expired and
            self.view_count < self.max_views
        )
    
    def generate_access_url(self, base_url: str = None) -> str:
        """Generate the full access URL for the patient."""
        if not base_url:
            base_url = "https://soapify.app"  # Default base URL
        return f"{base_url}/patient/{self.link_id}/?token={self.access_token}"


class OutputFile(models.Model):
    """
    Generated output files (PDF, JSON, Markdown).
    """
    FILE_TYPE_CHOICES = [
        ('pdf_doctor', 'PDF for Doctor'),
        ('pdf_patient', 'PDF for Patient'),
        ('json', 'JSON Export'),
        ('markdown', 'Markdown Export'),
    ]
    
    finalized_soap = models.ForeignKey(
        FinalizedSOAP,
        on_delete=models.CASCADE,
        related_name='output_files'
    )
    
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_path = models.CharField(max_length=500, help_text="S3 object key")
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    presigned_url = models.URLField(blank=True, help_text="Pre-signed download URL")
    presigned_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Generation metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    generation_time_seconds = models.FloatField(null=True, blank=True)
    template_version = models.CharField(max_length=20, default='v1.0')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'output_files'
        unique_together = ['finalized_soap', 'file_type']
        indexes = [
            models.Index(fields=['finalized_soap', 'file_type']),
            models.Index(fields=['generated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_file_type_display()} for {self.finalized_soap.patient_ref}"
    
    @property
    def is_presigned_url_valid(self):
        from django.utils import timezone
        return (
            self.presigned_url and
            self.presigned_expires_at and
            timezone.now() < self.presigned_expires_at
        )
    
    def get_file_size_mb(self):
        """Get file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)


class DeliveryLog(models.Model):
    """
    Log of delivery attempts for patient links.
    """
    DELIVERY_STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    patient_link = models.ForeignKey(
        PatientLink,
        on_delete=models.CASCADE,
        related_name='delivery_logs'
    )
    
    delivery_method = models.CharField(max_length=20)
    recipient = models.CharField(max_length=255, help_text="Phone number or email")
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='queued')
    
    # Provider details
    provider = models.CharField(max_length=50, help_text="SMS/Email provider used")
    provider_message_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, help_text="Provider API response")
    
    # Timing
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        db_table = 'delivery_logs'
        indexes = [
            models.Index(fields=['patient_link', 'status']),
            models.Index(fields=['status', 'queued_at']),
        ]
    
    def __str__(self):
        return f"Delivery to {self.recipient} ({self.status})"
    
    @property
    def can_retry(self):
        return self.status == 'failed' and self.retry_count < self.max_retries
