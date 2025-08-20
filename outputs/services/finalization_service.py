"""
SOAP finalization service using GPT-4o via GapGPT.
"""

import json
import logging
import time
from typing import Dict, Optional
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class FinalizationService:
    """Service for finalizing SOAP drafts using GPT-4o."""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = "gpt-4o"
        self.max_tokens = 4000
        self.temperature = 0.2  # Slightly higher for more natural language
        self.max_retries = 3
    
    def finalize_soap_draft(
        self,
        soap_draft_data: Dict,
        encounter_context: Optional[Dict] = None
    ) -> Dict:
        """
        Finalize SOAP draft using GPT-4o for better language and completeness.
        
        Args:
            soap_draft_data: Raw SOAP draft data
            encounter_context: Additional encounter context
            
        Returns:
            Dict containing finalized SOAP data and metadata
        """
        start_time = time.time()
        
        try:
            # Prepare system prompt
            system_prompt = self._build_finalization_system_prompt()
            
            # Prepare user prompt
            user_prompt = self._build_finalization_user_prompt(soap_draft_data, encounter_context)
            
            logger.info("Starting SOAP finalization with GPT-4o")
            
            # Call GPT-4o
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
            finalized_data = json.loads(response_text)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(finalized_data, soap_draft_data)
            
            logger.info(
                f"SOAP finalization completed in {processing_time:.2f}s. "
                f"Quality score: {quality_score:.3f}"
            )
            
            return {
                'finalized_data': finalized_data,
                'quality_score': quality_score,
                'processing_time': processing_time,
                'tokens_used': response.usage.total_tokens if response.usage else None,
                'model_used': self.model
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from GPT-4o: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"SOAP finalization failed: {e}")
            raise
    
    def _build_finalization_system_prompt(self) -> str:
        """Build system prompt for SOAP finalization."""
        return """You are an expert medical AI assistant specialized in finalizing and polishing medical SOAP notes.

Your task is to review and enhance a SOAP draft, ensuring:

1. **Medical Accuracy**: Verify medical terminology and clinical reasoning
2. **Completeness**: Fill in logical gaps and ensure comprehensive documentation
3. **Professional Language**: Use appropriate medical terminology and clear language
4. **Consistency**: Ensure all sections align and support each other
5. **Persian Language**: Maintain proper Persian medical terminology where applicable
6. **Structure**: Follow standard SOAP format and medical documentation standards

Guidelines:
- Enhance the existing content without changing the core medical facts
- Add relevant details that would be expected in a complete SOAP note
- Use proper medical terminology and abbreviations
- Ensure clinical reasoning is clear and logical
- Maintain the original JSON structure
- Do not add information that contradicts the original draft

Output must be a complete, professional SOAP note in the same JSON format."""

    def _build_finalization_user_prompt(self, soap_draft_data: Dict, encounter_context: Optional[Dict] = None) -> str:
        """Build user prompt for finalization."""
        context_text = ""
        if encounter_context:
            context_text = f"\nEncounter Context:\n{json.dumps(encounter_context, ensure_ascii=False, indent=2)}\n"
        
        return f"""Please finalize and enhance this SOAP draft:

{context_text}
SOAP Draft to Finalize:
{json.dumps(soap_draft_data, ensure_ascii=False, indent=2)}

Please review and enhance this SOAP note by:
1. Improving medical language and terminology
2. Ensuring completeness and logical flow
3. Adding standard medical documentation elements where appropriate
4. Maintaining clinical accuracy and consistency
5. Using proper Persian medical terms where applicable

Return the finalized SOAP note in the same JSON structure, enhanced and professionally written."""

    def _calculate_quality_score(self, finalized_data: Dict, original_data: Dict) -> float:
        """Calculate quality score by comparing finalized vs original data."""
        try:
            # Count improvements
            improvements = 0
            total_fields = 0
            
            def compare_sections(final_obj, original_obj, path=""):
                nonlocal improvements, total_fields
                
                if isinstance(final_obj, dict) and isinstance(original_obj, dict):
                    all_keys = set(final_obj.keys()) | set(original_obj.keys())
                    for key in all_keys:
                        total_fields += 1
                        final_value = final_obj.get(key, "")
                        original_value = original_obj.get(key, "")
                        
                        # Check for improvements
                        if isinstance(final_value, str) and isinstance(original_value, str):
                            if len(final_value.strip()) > len(original_value.strip()) * 1.2:
                                improvements += 1
                        elif isinstance(final_value, (dict, list)) and isinstance(original_value, (dict, list)):
                            compare_sections(final_value, original_value, f"{path}.{key}")
            
            compare_sections(finalized_data, original_data)
            
            # Base quality score
            base_score = 0.7  # Assume good baseline quality
            
            # Improvement bonus
            if total_fields > 0:
                improvement_ratio = improvements / total_fields
                improvement_bonus = min(improvement_ratio * 0.3, 0.3)
                base_score += improvement_bonus
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to calculate quality score: {e}")
            return 0.8  # Default good quality
    
    def enhance_for_patient_version(self, finalized_data: Dict) -> Dict:
        """
        Create patient-friendly version of the SOAP note.
        
        Args:
            finalized_data: Finalized SOAP data
            
        Returns:
            Patient-friendly version with simplified language
        """
        try:
            # Prepare system prompt for patient version
            system_prompt = """You are a medical communication expert. Convert this medical SOAP note into a patient-friendly summary.

Guidelines:
1. Use simple, non-medical language
2. Explain medical terms in parentheses
3. Focus on what the patient needs to know
4. Include clear instructions and follow-up steps
5. Maintain accuracy while improving readability
6. Use Persian language where appropriate for better patient understanding

Structure the output as a patient summary with sections:
- Your Visit Summary
- What We Found
- Your Diagnosis
- Your Treatment Plan
- Next Steps
- Important Notes"""

            user_prompt = f"""Please convert this medical SOAP note into a patient-friendly summary:

{json.dumps(finalized_data, ensure_ascii=False, indent=2)}

Create a clear, understandable summary that the patient can easily read and follow."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            patient_version = json.loads(response.choices[0].message.content)
            
            logger.info("Created patient-friendly version of SOAP note")
            return patient_version
            
        except Exception as e:
            logger.error(f"Failed to create patient version: {e}")
            # Return simplified version as fallback
            return self._create_simple_patient_summary(finalized_data)
    
    def _create_simple_patient_summary(self, finalized_data: Dict) -> Dict:
        """Create a simple patient summary as fallback."""
        return {
            "visit_summary": finalized_data.get('subjective', {}).get('chief_complaint', 'Medical consultation'),
            "findings": finalized_data.get('objective', {}).get('physical_examination', {}).get('general_appearance', 'Examination completed'),
            "diagnosis": finalized_data.get('assessment', {}).get('primary_diagnosis', 'Diagnosis provided'),
            "treatment": str(finalized_data.get('plan', {}).get('treatment_plan', 'Treatment plan discussed')),
            "next_steps": finalized_data.get('plan', {}).get('follow_up', {}).get('next_appointment', 'Follow-up as needed'),
            "notes": "Please contact your doctor if you have any questions about this summary."
        }
