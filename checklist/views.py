"""
Checklist views for SOAPify.
"""
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ChecklistCatalog, ChecklistEval, ChecklistTemplate
from .serializers import (
    ChecklistCatalogSerializer, ChecklistEvalSerializer,
    ChecklistSummarySerializer, ChecklistTemplateSerializer
)
from .services import ChecklistEvaluationService


class ChecklistCatalogViewSet(viewsets.ModelViewSet):
    """ViewSet for managing checklist catalog items."""
    
    queryset = ChecklistCatalog.objects.all()
    serializer_class = ChecklistCatalogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating a new catalog item."""
        serializer.save(created_by=self.request.user)


class ChecklistEvalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing checklist evaluations."""
    
    queryset = ChecklistEval.objects.select_related('catalog_item', 'encounter')
    serializer_class = ChecklistEvalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by encounter
        encounter_id = self.request.query_params.get('encounter_id')
        if encounter_id:
            queryset = queryset.filter(encounter_id=encounter_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter items that need attention
        needs_attention = self.request.query_params.get('needs_attention')
        if needs_attention and needs_attention.lower() == 'true':
            queryset = queryset.filter(
                Q(status__in=['missing', 'unclear']) |
                Q(status='partial', confidence_score__lt=0.7)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get checklist summary for an encounter."""
        encounter_id = request.query_params.get('encounter_id')
        if not encounter_id:
            return Response(
                {'error': 'encounter_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all evaluations for the encounter
        evals = ChecklistEval.objects.filter(encounter_id=encounter_id)
        
        # Calculate summary statistics
        total_items = evals.count()
        if total_items == 0:
            return Response({
                'total_items': 0,
                'covered_items': 0,
                'missing_items': 0,
                'partial_items': 0,
                'unclear_items': 0,
                'coverage_percentage': 0.0,
                'needs_attention': []
            })
        
        status_counts = evals.values('status').annotate(count=Count('status'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        covered_items = status_dict.get('covered', 0)
        missing_items = status_dict.get('missing', 0)
        partial_items = status_dict.get('partial', 0)
        unclear_items = status_dict.get('unclear', 0)
        
        coverage_percentage = (covered_items / total_items) * 100
        
        # Get items that need attention
        needs_attention_evals = evals.filter(
            Q(status__in=['missing', 'unclear']) |
            Q(status='partial', confidence_score__lt=0.7)
        )
        
        needs_attention_data = ChecklistEvalSerializer(
            needs_attention_evals, many=True
        ).data
        
        summary_data = {
            'total_items': total_items,
            'covered_items': covered_items,
            'missing_items': missing_items,
            'partial_items': partial_items,
            'unclear_items': unclear_items,
            'coverage_percentage': round(coverage_percentage, 2),
            'needs_attention': needs_attention_data
        }
        
        serializer = ChecklistSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def evaluate_encounter(self, request):
        """Trigger checklist evaluation for an encounter."""
        encounter_id = request.data.get('encounter_id')
        template_id = request.data.get('template_id')
        
        if not encounter_id:
            return Response(
                {'error': 'encounter_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Use the evaluation service to process the encounter
            service = ChecklistEvaluationService()
            results = service.evaluate_encounter(encounter_id, template_id)
            
            return Response({
                'message': 'Checklist evaluation completed',
                'results': results
            })
        
        except Exception as e:
            return Response(
                {'error': f'Evaluation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChecklistTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing checklist templates."""
    
    queryset = ChecklistTemplate.objects.prefetch_related('catalog_items')
    serializer_class = ChecklistTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by specialty
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
        
        # Show only default templates
        default_only = self.request.query_params.get('default_only')
        if default_only and default_only.lower() == 'true':
            queryset = queryset.filter(is_default=True)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by field when creating a new template."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def catalog_items(self, request, pk=None):
        """Get catalog items for this template."""
        template = self.get_object()
        catalog_items = template.catalog_items.filter(is_active=True)
        serializer = ChecklistCatalogSerializer(catalog_items, many=True)
        return Response(serializer.data)