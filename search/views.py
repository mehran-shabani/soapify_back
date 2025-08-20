"""
Search views for SOAPify.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date

from .services import HybridSearchService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_content(request):
    """
    Perform hybrid search across all content.
    
    Query parameters:
    - q: Search query (required)
    - encounter_id: Filter by encounter ID
    - content_type: Filter by content type (transcript, soap, checklist, notes)
    - date_from: Filter by date from (YYYY-MM-DD)
    - date_to: Filter by date to (YYYY-MM-DD)
    - page: Page number for pagination
    - page_size: Number of results per page (default: 20)
    """
    query_text = request.GET.get('q', '').strip()
    
    if not query_text:
        return Response(
            {'error': 'Query parameter "q" is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build filters
    filters = {}
    
    if request.GET.get('encounter_id'):
        try:
            filters['encounter_id'] = int(request.GET.get('encounter_id'))
        except ValueError:
            return Response(
                {'error': 'Invalid encounter_id format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if request.GET.get('content_type'):
        content_types = request.GET.getlist('content_type')
        valid_types = ['encounter', 'transcript', 'soap', 'checklist', 'notes']
        invalid_types = [ct for ct in content_types if ct not in valid_types]
        
        if invalid_types:
            return Response(
                {
                    'error': f'Invalid content types: {invalid_types}',
                    'valid_types': valid_types
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters['content_type'] = content_types
    
    if request.GET.get('date_from'):
        date_from = parse_date(request.GET.get('date_from'))
        if not date_from:
            return Response(
                {'error': 'Invalid date_from format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        filters['date_from'] = date_from
    
    if request.GET.get('date_to'):
        date_to = parse_date(request.GET.get('date_to'))
        if not date_to:
            return Response(
                {'error': 'Invalid date_to format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        filters['date_to'] = date_to
    
    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)  # Max 100 results per page
    
    # Perform search
    search_service = HybridSearchService()
    search_results = search_service.search(
        query_text=query_text,
        user=request.user,
        filters=filters,
        limit=page_size * 5  # Get more results for better pagination
    )
    
    # Paginate results
    paginator = Paginator(search_results['results'], page_size)
    page_obj = paginator.get_page(page)
    
    return Response({
        'query': query_text,
        'filters': filters,
        'results': list(page_obj),
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_results': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        },
        'execution_time_ms': search_results['execution_time_ms'],
        'search_id': search_results['search_id']
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_suggestions(request):
    """
    Get search suggestions based on query prefix.
    
    Query parameters:
    - q: Query prefix (required)
    - limit: Maximum number of suggestions (default: 10)
    """
    query_prefix = request.GET.get('q', '').strip()
    
    if not query_prefix or len(query_prefix) < 2:
        return Response(
            {'error': 'Query prefix must be at least 2 characters'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    limit = min(int(request.GET.get('limit', 10)), 20)
    
    # Get suggestions from recent searches
    from .models import SearchQuery as SearchQueryModel
    
    suggestions = SearchQueryModel.objects.filter(
        query_text__icontains=query_prefix,
        results_count__gt=0  # Only suggest queries that returned results
    ).values('query_text').distinct().order_by('-id')[:limit]
    
    suggestion_list = [s['query_text'] for s in suggestions]
    
    return Response({
        'query_prefix': query_prefix,
        'suggestions': suggestion_list
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reindex_encounter(request):
    """
    Reindex all content for a specific encounter.
    
    Body parameters:
    - encounter_id: ID of the encounter to reindex (required)
    """
    encounter_id = request.data.get('encounter_id')
    
    if not encounter_id:
        return Response(
            {'error': 'encounter_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        encounter_id = int(encounter_id)
    except ValueError:
        return Response(
            {'error': 'Invalid encounter_id format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        search_service = HybridSearchService()
        results = search_service.reindex_encounter(encounter_id)
        
        return Response({
            'message': f'Successfully reindexed encounter {encounter_id}',
            'results': results
        })
    
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        return Response(
            {'error': f'Reindexing failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_analytics(request):
    """
    Get search analytics.
    
    Query parameters:
    - days: Number of days to analyze (default: 30)
    """
    days = int(request.GET.get('days', 30))
    
    if days < 1 or days > 365:
        return Response(
            {'error': 'Days parameter must be between 1 and 365'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        search_service = HybridSearchService()
        analytics = search_service.get_search_analytics(days=days)
        
        return Response(analytics)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to get analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )