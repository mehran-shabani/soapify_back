from django.urls import path
from .views import start_soap_extraction, get_soap_draft, update_soap_section, get_checklist, update_checklist_item

app_name = 'nlp'

urlpatterns = [
    path('generate/<str:encounter_id>/', start_soap_extraction, name='generate-soap'),
    path('drafts/<str:encounter_id>/', get_soap_draft, name='list-drafts'),
    path('drafts/<str:encounter_id>/', get_soap_draft, name='get-draft'),
    path('drafts/<str:encounter_id>/update-section/', update_soap_section, name='update-section'),
    path('drafts/<str:encounter_id>/checklist/', get_checklist, name='get-checklist'),
    path('drafts/<str:encounter_id>/checklist/<str:item_id>/', update_checklist_item, name='update-checklist-item'),
]