"""
Template service for generating Markdown and HTML from SOAP data.
"""

import logging
from typing import Dict
from datetime import datetime
from django.template import Template, Context
from django.template.loader import get_template

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for generating formatted output from SOAP data."""
    
    def __init__(self):
        self.template_version = "v1.0"
    
    def generate_markdown_doctor(self, finalized_data: Dict, metadata: Dict) -> str:
        """
        Generate Markdown format for doctor's use.
        
        Args:
            finalized_data: Finalized SOAP data
            metadata: Additional metadata (patient, doctor, date, etc.)
            
        Returns:
            Formatted Markdown string
        """
        try:
            template_content = self._get_doctor_markdown_template()
            template = Template(template_content)
            
            context_data = {
                'soap': finalized_data,
                'metadata': metadata,
                'generated_at': datetime.now(),
                'template_version': self.template_version
            }
            
            context = Context(context_data)
            markdown_content = template.render(context)
            
            logger.info("Generated doctor Markdown document")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Failed to generate doctor Markdown: {e}")
            raise
    
    def generate_markdown_patient(self, patient_summary: Dict, metadata: Dict) -> str:
        """
        Generate patient-friendly Markdown format.
        
        Args:
            patient_summary: Patient-friendly summary data
            metadata: Additional metadata
            
        Returns:
            Patient-friendly Markdown string
        """
        try:
            template_content = self._get_patient_markdown_template()
            template = Template(template_content)
            
            context_data = {
                'summary': patient_summary,
                'metadata': metadata,
                'generated_at': datetime.now(),
                'template_version': self.template_version
            }
            
            context = Context(context_data)
            markdown_content = template.render(context)
            
            logger.info("Generated patient Markdown document")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Failed to generate patient Markdown: {e}")
            raise
    
    def generate_html_from_markdown(self, markdown_content: str) -> str:
        """
        Convert Markdown to HTML for PDF generation.
        
        Args:
            markdown_content: Markdown content string
            
        Returns:
            HTML string with CSS styling
        """
        try:
            import markdown
            
            # Convert Markdown to HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=['tables', 'fenced_code', 'toc']
            )
            
            # Add CSS styling
            css_styles = self._get_pdf_css_styles()
            
            full_html = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="fa">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>SOAP Note</title>
                <style>{css_styles}</style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            logger.info("Converted Markdown to HTML")
            return full_html
            
        except ImportError:
            logger.warning("Markdown library not available, using simple conversion")
            return self._simple_markdown_to_html(markdown_content)
        except Exception as e:
            logger.error(f"Failed to convert Markdown to HTML: {e}")
            raise
    
    def _get_doctor_markdown_template(self) -> str:
        """Get Markdown template for doctor's version."""
        return """# گزارش پزشکی SOAP

**بیمار:** {{ metadata.patient_ref }}  
**پزشک:** {{ metadata.doctor_name }}  
**تاریخ ویزیت:** {{ metadata.encounter_date|date:"Y/m/d H:i" }}  
**تاریخ تولید گزارش:** {{ generated_at|date:"Y/m/d H:i" }}

---

## بخش ذهنی (Subjective)

### شکایت اصلی
{{ soap.subjective.chief_complaint|default:"ثبت نشده" }}

### تاریخچه بیماری فعلی
{{ soap.subjective.history_present_illness|default:"ثبت نشده" }}

{% if soap.subjective.past_medical_history %}
### سابقه پزشکی
{{ soap.subjective.past_medical_history }}
{% endif %}

{% if soap.subjective.medications %}
### داروهای فعلی
{% for med in soap.subjective.medications %}
- **{{ med.name }}**: {{ med.dosage }} {{ med.frequency }}{% if med.duration %} برای {{ med.duration }}{% endif %}
{% endfor %}
{% endif %}

{% if soap.subjective.allergies %}
### آلرژی‌ها
{% for allergy in soap.subjective.allergies %}
- **{{ allergy.allergen }}**: {{ allergy.reaction }} ({{ allergy.severity }})
{% endfor %}
{% endif %}

---

## بخش عینی (Objective)

{% if soap.objective.vital_signs %}
### علائم حیاتی
{% for key, value in soap.objective.vital_signs.items %}
{% if value %}
- **{{ key|title }}**: {{ value }}
{% endif %}
{% endfor %}
{% endif %}

{% if soap.objective.physical_examination %}
### معاینه فیزیکی
{% for system, findings in soap.objective.physical_examination.items %}
{% if findings %}
- **{{ system|title }}**: {{ findings }}
{% endif %}
{% endfor %}
{% endif %}

{% if soap.objective.laboratory_results %}
### نتایج آزمایشگاهی
{% for lab in soap.objective.laboratory_results %}
- **{{ lab.test_name }}**: {{ lab.result }}{% if lab.reference_range %} (مرجع: {{ lab.reference_range }}){% endif %}
{% endfor %}
{% endif %}

---

## بخش ارزیابی (Assessment)

### تشخیص اصلی
{{ soap.assessment.primary_diagnosis|default:"ثبت نشده" }}

{% if soap.assessment.clinical_reasoning %}
### استدلال بالینی
{{ soap.assessment.clinical_reasoning }}
{% endif %}

{% if soap.assessment.differential_diagnoses %}
### تشخیص‌های افتراقی
{% for diff in soap.assessment.differential_diagnoses %}
- **{{ diff.diagnosis }}**: احتمال {{ diff.probability|default:"نامشخص" }}
{% endfor %}
{% endif %}

---

## بخش برنامه (Plan)

{% if soap.plan.treatment_plan.medications %}
### داروهای تجویزی
{% for med in soap.plan.treatment_plan.medications %}
- **{{ med.medication }}**: {{ med.dosage }} {{ med.frequency }}{% if med.duration %} برای {{ med.duration }}{% endif %}
  {% if med.instructions %}
  - دستورات: {{ med.instructions }}
  {% endif %}
{% endfor %}
{% endif %}

{% if soap.plan.follow_up %}
### برنامه پیگیری
{% for key, value in soap.plan.follow_up.items %}
{% if value %}
- **{{ key|title }}**: {{ value }}
{% endif %}
{% endfor %}
{% endif %}

{% if soap.plan.referrals %}
### ارجاعات
{% for ref in soap.plan.referrals %}
- **{{ ref.specialty }}**: {{ ref.reason }} ({{ ref.urgency }})
{% endfor %}
{% endif %}

---

*تولید شده توسط سیستم SOAPify - نسخه {{ template_version }}*
"""

    def _get_patient_markdown_template(self) -> str:
        """Get Markdown template for patient's version."""
        return """# خلاصه ویزیت پزشکی

**تاریخ ویزیت:** {{ metadata.encounter_date|date:"Y/m/d" }}  
**پزشک معالج:** {{ metadata.doctor_name }}  
**شماره پرونده:** {{ metadata.patient_ref }}

---

## خلاصه ویزیت شما
{{ summary.visit_summary|default:"ویزیت پزشکی انجام شد" }}

## یافته‌های معاینه
{{ summary.findings|default:"معاینه انجام شد" }}

## تشخیص
{{ summary.diagnosis|default:"تشخیص ارائه شد" }}

## برنامه درمانی شما
{{ summary.treatment|default:"برنامه درمانی تعیین شد" }}

## مراحل بعدی
{{ summary.next_steps|default:"پیگیری در صورت نیاز" }}

---

## نکات مهم
{{ summary.notes|default:"در صورت داشتن سوال با پزشک معالج تماس بگیرید" }}

---

*این خلاصه برای اطلاع شما تهیه شده است. در صورت داشتن سوال با پزشک معالج تماس بگیرید.*

**تاریخ تولید:** {{ generated_at|date:"Y/m/d H:i" }}
"""

    def _get_pdf_css_styles(self) -> str:
        """Get CSS styles for PDF generation with Persian font support."""
        return """
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
        
        body {
            font-family: 'Vazirmatn', Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            margin: 2cm;
            direction: rtl;
            text-align: right;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        
        h1 {
            font-size: 18pt;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.3em;
        }
        
        h2 {
            font-size: 16pt;
            color: #2980b9;
        }
        
        h3 {
            font-size: 14pt;
            color: #8e44ad;
        }
        
        ul, ol {
            margin: 0.5em 0;
            padding-right: 1.5em;
        }
        
        li {
            margin: 0.3em 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: right;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        
        .metadata {
            background-color: #f8f9fa;
            padding: 1em;
            border-radius: 5px;
            margin-bottom: 2em;
        }
        
        .section {
            margin-bottom: 2em;
            page-break-inside: avoid;
        }
        
        .critical {
            background-color: #fff5f5;
            border-left: 4px solid #e53e3e;
            padding: 1em;
            margin: 1em 0;
        }
        
        .footer {
            margin-top: 3em;
            padding-top: 1em;
            border-top: 1px solid #ddd;
            font-size: 10pt;
            color: #666;
            text-align: center;
        }
        
        @media print {
            body {
                margin: 1cm;
            }
            
            .no-print {
                display: none;
            }
        }
        """
    
    def _simple_markdown_to_html(self, markdown_content: str) -> str:
        """Simple Markdown to HTML conversion as fallback."""
        html_content = markdown_content
        
        # Basic conversions
        html_content = html_content.replace('\n# ', '\n<h1>').replace('\n## ', '\n<h2>')
        html_content = html_content.replace('\n### ', '\n<h3>').replace('\n#### ', '\n<h4>')
        html_content = html_content.replace('\n---\n', '\n<hr>\n')
        html_content = html_content.replace('\n\n', '\n<p>')
        html_content = html_content.replace('**', '<strong>').replace('**', '</strong>')
        
        return f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="fa">
        <head>
            <meta charset="UTF-8">
            <style>{self._get_pdf_css_styles()}</style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
