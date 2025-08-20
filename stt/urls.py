from django.urls import path
from .views import (
    start_stt_processing,
    process_encounter_stt,
    get_transcript,
    get_encounter_transcript,
    update_transcript_segment,
    search_transcript,
    transcription_status,
    transcription_history,
    upload_and_transcribe,
    bulk_transcribe,
)

app_name = 'stt'

urlpatterns = [
    path('transcribe/', start_stt_processing, name='transcribe-chunk'),
    path('status/<str:task_id>/', transcription_status, name='transcription-status'),
    path('history/', transcription_history, name='transcription-history'),
    path('upload-transcribe/', upload_and_transcribe, name='upload-and-transcribe'),
    path('bulk-transcribe/', bulk_transcribe, name='bulk-transcribe'),
    path('encounter/<str:encounter_id>/process/', process_encounter_stt, name='process-encounter-stt'),
    path('transcript/<str:audio_chunk_id>/', get_transcript, name='get-transcript'),
    path('encounter/<str:encounter_id>/transcript/', get_encounter_transcript, name='get-encounter-transcript'),
    path('transcript/segment/<str:segment_id>/', update_transcript_segment, name='update-transcript-segment'),
    path('search/', search_transcript, name='search-transcript'),
]