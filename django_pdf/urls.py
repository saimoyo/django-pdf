from django.urls import path

from django_pdf.views import TemplateHTMX, DashboardView, HTMLTemplateView, \
    PDFTemplateView

app_name = "django_db"
urlpatterns = [
    path("pdf-templates/", TemplateHTMX.as_view(), name="pdf-templates"),
    path(
        "html-template/",
        HTMLTemplateView.as_view(),
        name="create-html-template"
    ),
    path(
        "html-template/<int:pk>/",
        HTMLTemplateView.as_view(),
        name="update-html-template"
    ),
    path(
        "pdf-template/",
        PDFTemplateView.as_view(),
        name="create-pdf-template"
    ),
    path(
        "pdf-template/<int:pk>/",
        PDFTemplateView.as_view(),
        name="update-pdf-template"
    ),
    path("", DashboardView.as_view(), name="pdf-dashboard"),
]
