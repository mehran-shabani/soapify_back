"""
SOAP extraction service using GPT-4o-mini via GapGPT.
"""

import json
import logging
import time
from typing import Dict, List, Optional
from django.conf import settings
from openai import OpenAI
from ..schemas.soap_schema import SOAP_SCHEMA, SOAP_CHECKLIST_ITEMS

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for extracting SOAP structure from transcript using GPT-4o-mini."""
    
    def __init__(self):
        # For tests, allow initialization without API key
        api_key = settings.OPENAI_API_KEY or "test-key"
        base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = "gpt-4o-mini"
        self.max_tokens = 4000
        self.temperature = 0.1  # Low temperature for consistent extraction
        self.max_retries = 3
    
    def extract_soap_from_transcript(
        self, 
        transcript_text: str,
        patient_context: Optional[Dict] = None
    ) -> Dict:
        """
        Extract SOAP structure from transcript text.
        
        Args:
            transcript_text: Full transcript text
            patient_context: Optional patient context for better extraction
            
        Returns:
            Dict containing extracted SOAP data and metadata
        """
        start_time = time.time()
        
        try:
            # Prepare system prompt
            system_prompt = self._build_system_prompt()
            
            # Prepare user prompt
            user_prompt = self._build_user_prompt(transcript_text, patient_context)
            
            logger.info(f"Starting SOAP extraction. Transcript length: {len(transcript_text)}")
            
            # Call GPT-4o-mini
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            processing_time = time.time() - start_time
            
            # Parse response
            response_text = response.choices[0].message.content
            extracted_data = json.loads(response_text)
            
            # Validate against schema
            validation_result = self._validate_soap_structure(extracted_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(extracted_data, transcript_text)
            
            logger.info(
                f"SOAP extraction completed in {processing_time:.2f}s. "
                f"Confidence: {confidence_score:.2f}, Valid: {validation_result['valid']}"
            )
            
            return {
                'soap_data': extracted_data,
                'confidence_score': confidence_score,
                'processing_time': processing_time,
                'tokens_used': response.usage.total_tokens if response.usage else None,
                'validation': validation_result,
                'model_used': self.model
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from GPT-4o-mini: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"SOAP extraction failed: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for SOAP extraction."""
        return """You are a medical AI assistant specialized in extracting structured SOAP notes from medical consultation transcripts in Persian/Farsi language.

Your task is to analyze the transcript and extract information into a structured SOAP format (Subjective, Objective, Assessment, Plan).

Guidelines:
1. Extract information accurately without adding details not mentioned in the transcript
2. Use the exact JSON schema structure provided
3. For missing information, use empty strings or null values
4. Maintain medical terminology and accuracy
5. Pay attention to Persian medical terms and context
6. If vital signs or measurements are mentioned, extract them precisely
7. Distinguish between patient-reported symptoms (Subjective) and doctor's observations (Objective)

Output must be valid JSON matching the provided schema."""

    def _build_user_prompt(self, transcript_text: str, patient_context: Optional[Dict] = None) -> str:
        """Build user prompt with transcript and context."""
        context_text = ""
        if patient_context:
            context_text = f"\nPatient Context: {json.dumps(patient_context, ensure_ascii=False)}\n"
        
        return f"""Please extract SOAP information from this medical consultation transcript:

{context_text}
Transcript:
{transcript_text}

Extract the information into this JSON structure:
{json.dumps(SOAP_SCHEMA, ensure_ascii=False, indent=2)}

Return only the JSON object with the extracted SOAP data."""

    def _validate_soap_structure(self, soap_data: Dict) -> Dict:
        """Validate extracted SOAP data against schema."""
        try:
            import jsonschema
            jsonschema.validate(soap_data, SOAP_SCHEMA)
            return {'valid': True, 'errors': []}
        except ImportError:
            # Basic validation if jsonschema not available
            required_sections = ['subjective', 'objective', 'assessment', 'plan', 'metadata']
            missing_sections = [sec for sec in required_sections if sec not in soap_data]
            
            if missing_sections:
                return {
                    'valid': False, 
                    'errors': [f'Missing required sections: {missing_sections}']
                }
            return {'valid': True, 'errors': []}
        except Exception as e:
            return {'valid': False, 'errors': [str(e)]}
    
    def _calculate_confidence_score(self, soap_data: Dict, transcript_text: str) -> float:
        """Calculate confidence score based on completeness and content quality."""
        try:
            # Base score from completeness
            total_fields = 0
            filled_fields = 0
            
            def count_fields(obj, prefix=""):
                nonlocal total_fields, filled_fields
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        total_fields += 1
                        if value and str(value).strip():
                            filled_fields += 1
                        if isinstance(value, (dict, list)):
                            count_fields(value, f"{prefix}.{key}")
                elif isinstance(obj, list):
                    for item in obj:
                        count_fields(item, prefix)
            
            count_fields(soap_data)
            
            completeness_score = filled_fields / total_fields if total_fields > 0 else 0
            
            # Bonus for critical sections
            critical_bonus = 0
            if soap_data.get('subjective', {}).get('chief_complaint'):
                critical_bonus += 0.1
            if soap_data.get('assessment', {}).get('primary_diagnosis'):
                critical_bonus += 0.1
            if soap_data.get('plan', {}).get('treatment_plan'):
                critical_bonus += 0.1
            
            # Text length factor (more content generally means better extraction)
            text_factor = min(len(transcript_text) / 1000, 1.0) * 0.1
            
            final_score = min(completeness_score + critical_bonus + text_factor, 1.0)
            return round(final_score, 3)
            
        except Exception as e:
            logger.warning(f"Failed to calculate confidence score: {e}")
            return 0.5  # Default moderate confidence
    
    def generate_checklist_items(self, soap_data: Dict) -> List[Dict]:
        """
        Generate dynamic checklist items based on SOAP data completeness.
        
        Args:
            soap_data: Extracted SOAP data
            
        Returns:
            List of checklist items with status assessment
        """
        checklist_items = []
        
        for item_template in SOAP_CHECKLIST_ITEMS:
            # Assess item status based on SOAP data
            status = self._assess_item_status(soap_data, item_template)
            
            # Calculate confidence in status assessment
            confidence = self._assess_item_confidence(soap_data, item_template, status)
            
            # Generate notes/suggestions
            notes = self._generate_item_notes(soap_data, item_template, status)
            
            checklist_item = {
                'item_id': item_template['id'],
                'section': item_template['section'],
                'title': item_template['title'],
                'description': item_template['description'],
                'item_type': 'required' if item_template['required'] else 'recommended',
                'status': status,
                'weight': item_template['weight'],
                'confidence': confidence,
                'notes': notes
            }
            
            checklist_items.append(checklist_item)
        
        return checklist_items
    
    def _assess_item_status(self, soap_data: Dict, item_template: Dict) -> str:
        """Assess the status of a checklist item based on SOAP data."""
        item_id = item_template['id']
        section = item_template['section']
        
        # Map item IDs to SOAP data paths
        field_mappings = {
            'chief_complaint': 'subjective.chief_complaint',
            'history_present_illness': 'subjective.history_present_illness',
            'vital_signs': 'objective.vital_signs',
            'physical_exam': 'objective.physical_examination',
            'primary_diagnosis': 'assessment.primary_diagnosis',
            'treatment_plan': 'plan.treatment_plan',
            'follow_up': 'plan.follow_up',
            'allergies': 'subjective.allergies',
            'medications': 'subjective.medications',
            'social_history': 'subjective.social_history'
        }
        
        field_path = field_mappings.get(item_id)
        if not field_path:
            return 'not_applicable'
        
        value = self._get_nested_value(soap_data, field_path)
        
        if not value:
            return 'missing'
        
        # Assess completeness based on content
        if isinstance(value, str):
            if len(value.strip()) < 10:
                return 'partial'
            return 'complete'
        elif isinstance(value, (list, dict)):
            if not value:
                return 'missing'
            # For complex objects, check if they have meaningful content
            content_str = json.dumps(value, ensure_ascii=False)
            if len(content_str.strip()) < 20:
                return 'partial'
            return 'complete'
        
        return 'complete' if value else 'missing'
    
    def _assess_item_confidence(self, soap_data: Dict, item_template: Dict, status: str) -> float:
        """Assess confidence in the status assessment."""
        # Base confidence based on status
        base_confidence = {
            'complete': 0.9,
            'partial': 0.7,
            'missing': 0.8,  # High confidence in detecting missing items
            'not_applicable': 0.95
        }.get(status, 0.5)
        
        # Adjust based on item importance
        if item_template['weight'] >= 8:
            base_confidence += 0.05  # More confident about important items
        
        return min(base_confidence, 1.0)
    
    def _generate_item_notes(self, soap_data: Dict, item_template: Dict, status: str) -> str:
        """Generate helpful notes for checklist items."""
        if status == 'missing':
            return f"Consider adding {item_template['title'].lower()} to complete this section."
        elif status == 'partial':
            return f"More detail needed for {item_template['title'].lower()}."
        elif status == 'complete':
            return "Information appears complete."
        else:
            return ""
    
    def _get_nested_value(self, data: Dict, path: str):
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
