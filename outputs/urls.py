from django.urls import path
from .views import start_finalization, get_finalized_soap, generate_download_url, create_patient_link, list_output_files, access_patient_soap

app_name = 'outputs'

urlpatterns = [
    path('finalize/', start_finalization, name='finalize-and-generate'),
    path('finalized/<str:encounter_id>/', get_finalized_soap, name='get-finalized'),
    path('download/<str:file_id>/', generate_download_url, name='download-report'),
    path('link-patient/', create_patient_link, name='link-patient'),
    path('files/<str:encounter_id>/', list_output_files, name='list-files'),
    path('access/<str:link_id>/', access_patient_soap, name='access-patient-soap'),
]