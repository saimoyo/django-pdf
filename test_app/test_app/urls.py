from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("pdf/", include("django_pdf.urls", namespace="django_pdf")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
