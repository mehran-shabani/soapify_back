from django.urls import path
from django.http import JsonResponse


def ping(_request):
	return JsonResponse({"ok": True})


urlpatterns = [
	path('ping/', ping, name='embeddings-ping'),
]

