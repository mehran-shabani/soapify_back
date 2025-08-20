"""
URL patterns for encounters app.
"""

from django.urls import path
from . import views

app_name = 'encounters'

urlpatterns = [
    # Encounter management
    path('encounters/', views.list_encounters, name='list_encounters'),
    path('encounters/create/', views.create_encounter, name='create-encounter'),
    path('encounters/<int:encounter_id>/', views.encounter_detail, name='encounter_detail'),
    
    # Audio file management
    path('audio/presigned-url/', views.get_presigned_url, name='get-presigned-url'),
    path('audio/commit/', views.commit_audio_file, name='commit-audio'),
]