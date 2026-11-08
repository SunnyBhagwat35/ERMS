from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.claims.urls")),
]

if settings.DEBUG:
    # Serve uploaded receipts in dev only; production should use S3/CloudFront.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
