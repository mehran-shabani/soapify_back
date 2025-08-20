"""
Models for NLP processing and SOAP draft management.
"""

from django.db import models
from django.utils import timezone

from encounters.models import Encounter


class SOAPDraft(models.Model):
    """
    SOAP draft extracted from transcript.
    """
    STATUS_CHOICES = [
        ('extracting', 'Extracting'),
        ('draft', 'Draft'),
        ('reviewed', 'Reviewed'),
        ('finalized', 'Finalized'),
        ('error', 'Error'),
    ]
    
    encounter = models.OneToOneField(
        Encounter, 
        on_delete=models.CASCADE, 
        related_name='soap_draft'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='extracting')
    soap_data = models.JSONField(default=dict, help_text="SOAP structure as JSON")
    confidence_score = models.FloatField(null=True, blank=True, help_text="Overall confidence score")
    extraction_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    
    class Meta:
        db_table = 'soap_drafts'
        indexes = [
            models.Index(fields=['encounter']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"SOAP Draft for Encounter {self.encounter.id} - {self.status}"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on filled required fields."""
        if not self.soap_data:
            return 0
        
        required_fields = [
            'subjective.chief_complaint',
            'subjective.history_present_illness',
            'objective.vital_signs',
            'objective.physical_examination',
            'assessment.primary_diagnosis',
            'plan.treatment_plan'
        ]
        
        filled_count = 0
        for field_path in required_fields:
            value = self._get_nested_value(self.soap_data, field_path)
            if value and str(value).strip():
                filled_count += 1
        
        return int((filled_count / len(required_fields)) * 100)
    
    def _get_nested_value(self, data, path):
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    @classmethod
    def get_latest(cls, encounter: 'encounters.models.Encounter'):
        latest = cls.objects.filter(encounter=encounter).order_by('-created_at').first()
        return latest

    def create_revision(self, new_soap_data: dict) -> 'SOAPDraft':
        return SOAPDraft.objects.create(
            encounter=self.encounter,
            status='draft',
            soap_data=new_soap_data,
            confidence_score=self.confidence_score,
            extraction_version=self.extraction_version,
            reviewed_at=None,
            version=(self.version or 1) + 1,
        )

    def save(self, *args, **kwargs):
        # Auto-increment version per encounter
        if self._state.adding and (not self.version or self.version == 1):
            with transaction.atomic():
                last = SOAPDraft.objects.select_for_update().filter(encounter=self.encounter).order_by('-version').first()
                if last:
                    self.version = last.version + 1
                else:
                    self.version = 1
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class SOAPSection(models.Model):
    """Separate sections of a SOAP draft for finer-grained updates."""
    SECTION_CHOICES = [
        ('subjective', 'Subjective'),
        ('objective', 'Objective'),
        ('assessment', 'Assessment'),
        ('plan', 'Plan'),
    ]

    soap_draft = models.ForeignKey(SOAPDraft, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=20, choices=SECTION_CHOICES)
    content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'soap_sections'
        indexes = [
            models.Index(fields=['soap_draft', 'section_type']),
        ]

    def __str__(self) -> str:
        return f"{self.section_type} - SOAP Draft {self.soap_draft.id}"


class ExtractionTask(models.Model):
    """Track asynchronous extraction/regeneration tasks against an encounter."""
    TASK_CHOICES = [
        ('full_soap', 'Full SOAP'),
        ('section_update', 'Section Update'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    encounter = models.ForeignKey('encounters.Encounter', on_delete=models.CASCADE, related_name='extraction_tasks')
    task_type = models.CharField(max_length=20, choices=TASK_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'extraction_tasks'
        indexes = [
            models.Index(fields=['encounter', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"ExtractionTask {self.task_type} - {self.status}"


class ChecklistItem(models.Model):
    """
    Dynamic checklist items for SOAP validation.
    """
    ITEM_TYPE_CHOICES = [
        ('required', 'Required'),
        ('recommended', 'Recommended'),
        ('optional', 'Optional'),
    ]
    
    STATUS_CHOICES = [
        ('missing', 'Missing'),
        ('partial', 'Partial'),
        ('complete', 'Complete'),
        ('not_applicable', 'Not Applicable'),
    ]
    
    soap_draft = models.ForeignKey(
        SOAPDraft,
        on_delete=models.CASCADE,
        related_name='checklist_items'
    )
    item_id = models.CharField(max_length=100, help_text="Unique identifier for checklist item")
    section = models.CharField(max_length=20, help_text="SOAP section (subjective/objective/assessment/plan)")
    title = models.CharField(max_length=200)
    description = models.TextField()
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='required')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='missing')
    weight = models.IntegerField(default=5, help_text="Importance weight (1-10)")
    confidence = models.FloatField(null=True, blank=True, help_text="AI confidence in status assessment")
    notes = models.TextField(blank=True, help_text="Additional notes or suggestions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checklist_items'
        unique_together = ['soap_draft', 'item_id']
        indexes = [
            models.Index(fields=['soap_draft', 'status']),
            models.Index(fields=['section', 'item_type']),
            models.Index(fields=['status', 'weight']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.status})"
    
    @property
    def is_critical(self):
        """Check if this is a critical checklist item."""
        return self.item_type == 'required' and self.weight >= 8
    
    @property
    def completion_score(self):
        """Calculate completion score based on status and weight."""
        status_scores = {
            'complete': 1.0,
            'partial': 0.5,
            'missing': 0.0,
            'not_applicable': 1.0  # N/A items are considered complete
        }
        return status_scores.get(self.status, 0.0) * self.weight


class ExtractionLog(models.Model):
    """
    Log of extraction attempts and results.
    """
    soap_draft = models.ForeignKey(
        SOAPDraft,
        on_delete=models.CASCADE,
        related_name='extraction_logs'
    )
    model_used = models.CharField(max_length=50, default='gpt-4o-mini')
    prompt_version = models.CharField(max_length=20, default='v1.0')
    input_text_length = models.IntegerField()
    output_json_length = models.IntegerField(null=True, blank=True)
    processing_time_seconds = models.FloatField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'extraction_logs'
        indexes = [
            models.Index(fields=['soap_draft', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"Extraction {status} for {self.soap_draft} at {self.created_at}"
