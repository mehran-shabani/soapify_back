"""
GapGPT client for SOAPify.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Union
import openai
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GapGPTClient:
    """Client for GapGPT API integration."""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        
        # Configure OpenAI client
        openai.api_key = self.api_key
        if self.base_url:
            openai.api_base = self.base_url
    
    def create_chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4o-mini",
                             temperature: float = 0.7, max_tokens: Optional[int] = None,
                             **kwargs) -> Dict[str, Any]:
        """
        Create a chat completion.
        
        Args:
            messages: List of message objects
            model: Model to use (gpt-4o-mini, gpt-4o, etc.)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            Chat completion response
        """
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            logger.info(f"Chat completion successful: {model}, tokens: {response.usage.total_tokens}")
            return response
        
        except openai.error.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            # Implement exponential backoff
            time.sleep(2)
            raise
        
        except openai.error.InvalidRequestError as e:
            logger.error(f"Invalid request: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise
    
    def create_embedding(self, input_text: Union[str, List[str]], 
                        model: str = "text-embedding-ada-002") -> Dict[str, Any]:
        """
        Create embeddings for text.
        
        Args:
            input_text: Text or list of texts to embed
            model: Embedding model to use
        
        Returns:
            Embedding response
        """
        try:
            # Check cache first for single text inputs
            if isinstance(input_text, str):
                cache_key = f"embedding:{hash(input_text)}:{model}"
                cached_result = cache.get(cache_key)
                if cached_result:
                    return cached_result
            
            response = openai.Embedding.create(
                input=input_text,
                model=model
            )
            
            # Cache single text embeddings
            if isinstance(input_text, str):
                cache.set(cache_key, response, timeout=3600)  # 1 hour
            
            logger.info(f"Embedding successful: {model}, inputs: {len(input_text) if isinstance(input_text, list) else 1}")
            return response
        
        except Exception as e:
            logger.error(f"Embedding creation failed: {str(e)}")
            raise
    
    def transcribe_audio(self, audio_file, model: str = "whisper-1", 
                        language: Optional[str] = None, 
                        response_format: str = "json") -> Dict[str, Any]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_file: Audio file object or path
            model: Whisper model to use
            language: Optional language hint
            response_format: Response format (json, text, srt, verbose_json, vtt)
        
        Returns:
            Transcription response
        """
        try:
            params = {
                "file": audio_file,
                "model": model,
                "response_format": response_format
            }
            
            if language:
                params["language"] = language
            
            response = openai.Audio.transcribe(**params)
            
            logger.info(f"Audio transcription successful: {model}")
            return response
        
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            raise
    
    def generate_soap_draft(self, transcript_text: str) -> Dict[str, Any]:
        """
        Generate SOAP draft from transcript.
        
        Args:
            transcript_text: Transcript text
        
        Returns:
            SOAP draft response
        """
        messages = [
            {
                "role": "system",
                "content": """You are a medical AI assistant that generates SOAP notes from patient encounter transcripts.

Generate a structured SOAP note with the following sections:
- Subjective: Patient's reported symptoms, concerns, and history
- Objective: Observable findings, vital signs, examination results
- Assessment: Clinical impression and diagnosis
- Plan: Treatment plan, medications, follow-up instructions

Format your response as JSON with the following structure:
{
  "subjective": {
    "content": "...",
    "confidence": 0.8
  },
  "objective": {
    "content": "...",
    "confidence": 0.8
  },
  "assessment": {
    "content": "...",
    "confidence": 0.8
  },
  "plan": {
    "content": "...",
    "confidence": 0.8
  },
  "summary": "Brief summary of the encounter"
}

Include confidence scores (0.0-1.0) for each section based on the clarity and completeness of information in the transcript."""
            },
            {
                "role": "user",
                "content": f"Please generate a SOAP note from this patient encounter transcript:\n\n{transcript_text}"
            }
        ]
        
        try:
            response = self.create_chat_completion(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=1500
            )
            
            return {
                "soap_content": response.choices[0].message.content,
                "usage": response.usage,
                "model": response.model
            }
        
        except Exception as e:
            logger.error(f"SOAP draft generation failed: {str(e)}")
            raise
    
    def finalize_soap_note(self, draft_content: Dict[str, Any], 
                          transcript_text: str) -> Dict[str, Any]:
        """
        Finalize SOAP note using GPT-4o.
        
        Args:
            draft_content: Draft SOAP content
            transcript_text: Original transcript
        
        Returns:
            Final SOAP note
        """
        messages = [
            {
                "role": "system",
                "content": """You are a senior medical AI assistant that reviews and finalizes SOAP notes.

Review the provided draft SOAP note and original transcript to create a final, polished version.

Ensure:
1. Medical accuracy and appropriate terminology
2. Completeness of all relevant information
3. Proper clinical reasoning in Assessment
4. Comprehensive and actionable Plan
5. Professional medical documentation standards

Format your response as JSON with the same structure as the draft, but include additional fields:
{
  "subjective": {
    "content": "...",
    "confidence": 0.9,
    "changes_made": ["list of improvements"]
  },
  "objective": {
    "content": "...",
    "confidence": 0.9,
    "changes_made": ["list of improvements"]
  },
  "assessment": {
    "content": "...",
    "confidence": 0.9,
    "changes_made": ["list of improvements"]
  },
  "plan": {
    "content": "...",
    "confidence": 0.9,
    "changes_made": ["list of improvements"]
  },
  "summary": "Comprehensive summary",
  "quality_score": 0.95,
  "review_notes": "Notes about the review process"
}"""
            },
            {
                "role": "user",
                "content": f"Please review and finalize this SOAP note:\n\nDRAFT:\n{draft_content}\n\nORIGINAL TRANSCRIPT:\n{transcript_text}"
            }
        ]
        
        try:
            response = self.create_chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.2,
                max_tokens=2000
            )
            
            return {
                "final_soap_content": response.choices[0].message.content,
                "usage": response.usage,
                "model": response.model
            }
        
        except Exception as e:
            logger.error(f"SOAP finalization failed: {str(e)}")
            raise
    
    def evaluate_checklist_coverage(self, transcript_text: str, 
                                   checklist_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate checklist coverage in transcript.
        
        Args:
            transcript_text: Transcript text
            checklist_items: List of checklist items to evaluate
        
        Returns:
            Checklist evaluation results
        """
        checklist_text = "\n".join([
            f"- {item['title']}: {item['description']}" 
            for item in checklist_items
        ])
        
        messages = [
            {
                "role": "system",
                "content": """You are a medical AI assistant that evaluates whether clinical checklist items are covered in patient encounter transcripts.

For each checklist item, determine:
1. Coverage status: "covered", "partial", "missing", or "unclear"
2. Confidence score (0.0-1.0)
3. Evidence text from transcript (if covered)
4. Follow-up question (if not fully covered)

Format your response as JSON:
{
  "evaluations": [
    {
      "item_title": "...",
      "status": "covered|partial|missing|unclear",
      "confidence": 0.8,
      "evidence": "relevant text from transcript",
      "follow_up_question": "suggested question if needed"
    }
  ],
  "overall_coverage": 0.75,
  "summary": "Overall assessment"
}"""
            },
            {
                "role": "user",
                "content": f"Please evaluate coverage of these checklist items in the transcript:\n\nCHECKLIST:\n{checklist_text}\n\nTRANSCRIPT:\n{transcript_text}"
            }
        ]
        
        try:
            response = self.create_chat_completion(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=1500
            )
            
            return {
                "evaluation_results": response.choices[0].message.content,
                "usage": response.usage,
                "model": response.model
            }
        
        except Exception as e:
            logger.error(f"Checklist evaluation failed: {str(e)}")
            raise
    
    def extract_medical_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract medical entities from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Extracted entities
        """
        messages = [
            {
                "role": "system",
                "content": """You are a medical NLP assistant that extracts medical entities from clinical text.

Extract and categorize the following types of medical entities:
- Symptoms and complaints
- Diagnoses and conditions
- Medications and dosages
- Procedures and treatments
- Anatomical references
- Vital signs and measurements
- Temporal references
- Allergies and adverse reactions

Format your response as JSON:
{
  "entities": {
    "symptoms": ["list of symptoms"],
    "diagnoses": ["list of diagnoses"],
    "medications": ["list of medications"],
    "procedures": ["list of procedures"],
    "anatomy": ["list of anatomical references"],
    "vitals": ["list of vital signs"],
    "temporal": ["list of time references"],
    "allergies": ["list of allergies"]
  },
  "entity_count": 25,
  "confidence": 0.85
}"""
            },
            {
                "role": "user",
                "content": f"Please extract medical entities from this text:\n\n{text}"
            }
        ]
        
        try:
            response = self.create_chat_completion(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=1000
            )
            
            return {
                "entities": response.choices[0].message.content,
                "usage": response.usage,
                "model": response.model
            }
        
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models."""
        try:
            models = openai.Model.list()
            return {
                "available_models": [model.id for model in models.data],
                "total_count": len(models.data)
            }
        except Exception as e:
            logger.error(f"Failed to get model info: {str(e)}")
            return {"error": str(e)}
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def validate_api_key(self) -> bool:
        """
        Validate API key by making a simple request.
        
        Returns:
            True if API key is valid
        """
        try:
            self.get_model_info()
            return True
        except Exception:
            return False