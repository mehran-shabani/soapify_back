from django.urls import path

from . import views


urlpatterns = [
    path("session/create/", views.create_session),
    path("chunk/", views.upload_chunk),
    path("commit/", views.commit_session),
    path("final/<uuid:session_id>/", views.download_final),
    path("s3/presign/", views.s3_presign_upload),
    path("s3/confirm/", views.s3_confirm_upload),
]

