from django.utils.deprecation import MiddlewareMixin

class CSRFFreeAPIMiddleware(MiddlewareMixin):
    """
    Disable CSRF validation for API endpoints (prefix /api/).
    Admin panel & normal views keep CSRF enabled.
    """

    def process_request(self, request):
        if request.path.startswith("/api/"):
            # این فلگ داخلی باعث میشه CsrfViewMiddleware چک نکنه
            setattr(request, "_dont_enforce_csrf_checks", True)