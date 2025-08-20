"""
Checklist evaluation services for SOAPify.
"""
import re
import logging
from typing import List, Dict, Any, Optional

from django.db import transaction
from django.contrib.auth import get_user_model

from .models import ChecklistCatalog, ChecklistEval, ChecklistTemplate
from encounters.models import Encounter

logger = logging.getLogger(__name__)
User = get_user_model()


class ChecklistEvaluationService:
    """Service for evaluating checklist items against encounter transcripts."""
    
    def __init__(self):
        self.confidence_threshold = 0.6
    
    def evaluate_encounter(self, encounter_id: int, template_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Evaluate checklist items for an encounter.
        
        Args:
            encounter_id: ID of the encounter to evaluate
            template_id: Optional template ID to use specific checklist items
        
        Returns:
            Dict with evaluation results
        """
        try:
            encounter = Encounter.objects.get(id=encounter_id)
        except Encounter.DoesNotExist:
            raise ValueError(f"Encounter {encounter_id} not found")
        
        # Get transcript text
        transcript_text = self._get_encounter_transcript(encounter)
        if not transcript_text:
            logger.warning(f"No transcript found for encounter {encounter_id}")
            return {'message': 'No transcript available for evaluation'}
        
        # Get checklist items to evaluate
        if template_id:
            try:
                template = ChecklistTemplate.objects.get(id=template_id)
                catalog_items = template.catalog_items.filter(is_active=True)
            except ChecklistTemplate.DoesNotExist:
                raise ValueError(f"Template {template_id} not found")
        else:
            # Use all active catalog items
            catalog_items = ChecklistCatalog.objects.filter(is_active=True)
        
        results = []
        
        with transaction.atomic():
            for item in catalog_items:
                evaluation = self._evaluate_catalog_item(encounter, item, transcript_text)
                results.append(evaluation)
        
        return {
            'encounter_id': encounter_id,
            'evaluated_items': len(results),
            'results': results
        }


class ChecklistService:
    """Minimal facade service used by tests to create instances etc."""

    def create_instance(self, catalog_id: int, encounter_id: int):
        """Create a ChecklistEval for the given catalog and encounter as an instance placeholder."""
        from .models import ChecklistCatalog, ChecklistEval
        from encounters.models import Encounter
        catalog = ChecklistCatalog.objects.get(id=catalog_id)
        encounter = Encounter.objects.get(id=encounter_id)
        instance, _ = ChecklistEval.objects.get_or_create(
            encounter=encounter,
            catalog_item=catalog,
            defaults={'status': 'missing', 'confidence_score': 0.0}
        )
        return instance
    
    def _get_encounter_transcript(self, encounter: Encounter) -> str:
        """Get combined transcript text for an encounter."""
        # Get all transcript segments for this encounter
        segments = encounter.transcript_segments.all().order_by('start_time')
        
        if not segments.exists():
            return ""
        
        # Combine all transcript text
        transcript_parts = []
        for segment in segments:
            transcript_parts.append(segment.text)
        
        return " ".join(transcript_parts)
    
    def _evaluate_catalog_item(self, encounter: Encounter, item: ChecklistCatalog, transcript_text: str) -> Dict[str, Any]:
        """
        Evaluate a single catalog item against transcript.
        
        Args:
            encounter: Encounter object
            item: ChecklistCatalog item to evaluate
            transcript_text: Full transcript text
        
        Returns:
            Dict with evaluation results
        """
        # Check if evaluation already exists
        eval_obj, created = ChecklistEval.objects.get_or_create(
            encounter=encounter,
            catalog_item=item,
            defaults={
                'status': 'unclear',
                'confidence_score': 0.0,
                'evidence_text': '',
                'anchor_positions': [],
                'generated_question': '',
                'notes': ''
            }
        )
        
        # Perform keyword-based evaluation
        evaluation_result = self._keyword_based_evaluation(item, transcript_text)
        
        # Update evaluation object
        eval_obj.status = evaluation_result['status']
        eval_obj.confidence_score = evaluation_result['confidence_score']
        eval_obj.evidence_text = evaluation_result['evidence_text']
        eval_obj.anchor_positions = evaluation_result['anchor_positions']
        eval_obj.generated_question = evaluation_result['generated_question']
        eval_obj.notes = evaluation_result['notes']
        eval_obj.save()
        
        return {
            'catalog_item_id': item.id,
            'catalog_item_title': item.title,
            'status': eval_obj.status,
            'confidence_score': eval_obj.confidence_score,
            'evidence_text': eval_obj.evidence_text,
            'generated_question': eval_obj.generated_question
        }
    
    def _keyword_based_evaluation(self, item: ChecklistCatalog, transcript_text: str) -> Dict[str, Any]:
        """
        Perform keyword-based evaluation of a checklist item.
        
        Args:
            item: ChecklistCatalog item
            transcript_text: Full transcript text
        
        Returns:
            Dict with evaluation results
        """
        keywords = item.keywords or []
        if not keywords:
            return {
                'status': 'unclear',
                'confidence_score': 0.0,
                'evidence_text': '',
                'anchor_positions': [],
                'generated_question': item.question_template,
                'notes': 'No keywords defined for evaluation'
            }
        
        # Convert transcript to lowercase for case-insensitive matching
        transcript_lower = transcript_text.lower()
        
        # Find keyword matches
        matches = []
        matched_keywords = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Use word boundaries to avoid partial matches
            pattern = r'\\b' + re.escape(keyword_lower) + r'\\b'
            
            for match in re.finditer(pattern, transcript_lower):
                matches.append({
                    'keyword': keyword,
                    'start': match.start(),
                    'end': match.end(),
                    'context': self._extract_context(transcript_text, match.start(), match.end())
                })
                matched_keywords.append(keyword)
        
        # Calculate confidence score based on keyword coverage
        keyword_coverage = len(set(matched_keywords)) / len(keywords)
        
        # Determine status based on matches and confidence
        if not matches:
            status = 'missing'
            confidence_score = 0.0
        elif keyword_coverage >= 0.8:
            status = 'covered'
            confidence_score = min(0.9, keyword_coverage)
        elif keyword_coverage >= 0.5:
            status = 'partial'
            confidence_score = keyword_coverage * 0.8
        else:
            status = 'unclear'
            confidence_score = keyword_coverage * 0.6
        
        # Extract evidence text from matches
        evidence_parts = []
        anchor_positions = []
        
        for match in matches[:3]:  # Limit to top 3 matches
            evidence_parts.append(match['context'])
            anchor_positions.append([match['start'], match['end']])
        
        evidence_text = " ... ".join(evidence_parts)
        
        # Generate follow-up question if needed
        generated_question = ""
        if status in ['missing', 'unclear', 'partial']:
            generated_question = item.question_template
        
        return {
            'status': status,
            'confidence_score': confidence_score,
            'evidence_text': evidence_text,
            'anchor_positions': anchor_positions,
            'generated_question': generated_question,
            'notes': f"Found {len(matches)} keyword matches ({len(set(matched_keywords))}/{len(keywords)} unique keywords)"
        }
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 100) -> str:
        """
        Extract context around a match.
        
        Args:
            text: Full text
            start: Start position of match
            end: End position of match
            context_length: Number of characters to include on each side
        
        Returns:
            Context string
        """
        # Calculate context boundaries
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        # Extract context
        context = text[context_start:context_end]
        
        # Add ellipsis if we truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
        
        return context.strip()
    
    def get_evaluation_summary(self, encounter_id: int) -> Dict[str, Any]:
        """
        Get summary of checklist evaluations for an encounter.
        
        Args:
            encounter_id: ID of the encounter
        
        Returns:
            Dict with summary statistics
        """
        evals = ChecklistEval.objects.filter(encounter_id=encounter_id)
        
        total_items = evals.count()
        if total_items == 0:
            return {
                'total_items': 0,
                'coverage_percentage': 0.0,
                'needs_attention': 0
            }
        
        # Count by status
        status_counts = {}
        for eval_obj in evals:
            status = eval_obj.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        covered_items = status_counts.get('covered', 0)
        coverage_percentage = (covered_items / total_items) * 100
        
        # Count items that need attention
        needs_attention = evals.filter(
            status__in=['missing', 'unclear']
        ).count()
        
        # Add partial items with low confidence
        needs_attention += evals.filter(
            status='partial',
            confidence_score__lt=0.7
        ).count()
        
        return {
            'total_items': total_items,
            'covered_items': covered_items,
            'missing_items': status_counts.get('missing', 0),
            'partial_items': status_counts.get('partial', 0),
            'unclear_items': status_counts.get('unclear', 0),
            'coverage_percentage': round(coverage_percentage, 2),
            'needs_attention': needs_attention
        }