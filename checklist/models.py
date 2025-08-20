"""
Checklist models for SOAPify.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ChecklistCatalog(models.Model):
    """Catalog of checklist items and questions."""
    
    CATEGORY_CHOICES = [
        ('subjective', 'Subjective'),
        ('objective', 'Objective'),
        ('assessment', 'Assessment'),
        ('plan', 'Plan'),
        ('general', 'General'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    keywords = models.JSONField(default=list, help_text="Keywords to match in transcript")
    question_template = models.TextField(help_text="Template for generating questions")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_checklists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'priority', 'title']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.category.title()}: {self.title}"


class ChecklistEval(models.Model):
    """Evaluation of checklist items for an encounter."""
    
    STATUS_CHOICES = [
        ('covered', 'Covered'),
        ('missing', 'Missing'),
        ('partial', 'Partially Covered'),
        ('unclear', 'Unclear'),
    ]
    
    encounter = models.ForeignKey('encounters.Encounter', on_delete=models.CASCADE, related_name='checklist_evals')
    catalog_item = models.ForeignKey(ChecklistCatalog, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    confidence_score = models.FloatField(default=0.0, help_text="AI confidence score (0.0-1.0)")
    evidence_text = models.TextField(blank=True, help_text="Text from transcript that supports this evaluation")
    anchor_positions = models.JSONField(default=list, help_text="Character positions in transcript")
    generated_question = models.TextField(blank=True, help_text="Generated follow-up question")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['encounter', 'catalog_item']
        ordering = ['catalog_item__category', 'catalog_item__priority']
        indexes = [
            models.Index(fields=['encounter', 'status']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.encounter} - {self.catalog_item.title}: {self.status}"
    
    @property
    def is_covered(self):
        """Check if this checklist item is adequately covered."""
        return self.status == 'covered'
    
    @property
    def needs_attention(self):
        """Check if this item needs doctor's attention."""
        return self.status in ['missing', 'unclear'] or (
            self.status == 'partial' and self.confidence_score < 0.7
        )


class ChecklistTemplate(models.Model):
    """Templates for different types of encounters."""
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    specialty = models.CharField(max_length=50, blank=True)
    catalog_items = models.ManyToManyField(ChecklistCatalog, through='ChecklistTemplateItem')
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ChecklistTemplateItem(models.Model):
    """Through model for template-catalog relationships."""
    
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE)
    catalog_item = models.ForeignKey(ChecklistCatalog, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['template', 'catalog_item']
        ordering = ['order']


class ChecklistInstance(models.Model):
    """Simple instance placeholder for a checklist tied to an encounter."""
    encounter = models.ForeignKey('encounters.Encounter', on_delete=models.CASCADE)
    catalog = models.ForeignKey(ChecklistCatalog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['encounter', 'catalog']