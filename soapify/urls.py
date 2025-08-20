from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import HttpResponse

from rest_framework import routers, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

# OpenAPI / Swagger
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# در صورت نیاز به Router (فعلاً خالی)
router = routers.DefaultRouter()
# مثال:
# from accounts.views import UserViewSet
# router.register(r'users', UserViewSet, basename='user')

# Health endpoint ساده (برای Docker healthcheck)
def healthz(_request):
    return HttpResponse("ok", status=200)

schema_view = get_schema_view(
    openapi.Info(
        title="SOAPify API",
        default_version='v1',
        description="Official API documentation for SOAPify.",
        contact=openapi.Contact(email="support@soapify.app"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],  # در پروداکشن می‌توانید محدود کنید
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth (JWT) با Scoped throttling
    path('api/auth/token/',
         TokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/auth/token/refresh/',
         TokenRefreshView.as_view(),
         name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Router base
    path('api/', include(router.urls)),

    # Core apps
    path('api/', include('accounts.urls')),
    path('api/', include('encounters.urls')),
    path('api/stt/', include('stt.urls')),
    path('api/nlp/', include('nlp.urls')),
    path('api/outputs/', include('outputs.urls')),
    path('api/integrations/', include('integrations.urls')),
    path('api/uploads/', include('uploads.urls')),

    # New modules
    path('api/checklist/', include('checklist.urls')),
    path('api/embeddings/', include('embeddings.urls')),
    path('api/search/', include('search.urls')),
    path('api/analytics/', include('analytics.urls')),

    # Admin extras
    path('adminplus/', include('adminplus.urls')),

    # Healthcheck
    path('healthz/', healthz, name='healthz'),
]

# Swagger/Redoc فقط در صورت فعال بودن
if settings.SWAGGER_ENABLED:
    urlpatterns += [
        re_path(
            r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json',
        ),
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]
