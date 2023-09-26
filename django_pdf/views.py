from datetime import datetime
from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.views import View
from django.views.generic import TemplateView, UpdateView

from django_pdf.forms import FontFamilyForm, TemplateType, TemplateTypeForm
from django_pdf.models import BaseTemplate, HTMLTemplate, PDFTemplate


# Mixin for handling permission checks
class TemplatesPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = getattr(settings, "PDF_PERMISSIONS", [])


class DashboardView(TemplatesPermissionMixin, TemplateView):
    template_name = "django_pdf/dashboard/index.html"

    def get_context_data(self, **kwargs: Any) -> dict:
        return super().get_context_data(**kwargs) | {
            "type_form": TemplateTypeForm()
        }


# Base class for handling template views
class BaseTemplateView(TemplatesPermissionMixin, UpdateView):
    def generate_pdf(self, template: BaseTemplate) -> str:
        pdf_buffer = template.generate(template.example_context)
        current_hour = datetime.now().hour
        file_name = f"{template.PDF_TEMPLATE_DIR}/temp/{template.name}_{current_hour}.pdf"
        default_storage.delete(file_name)
        default_storage.save(file_name, pdf_buffer)
        return default_storage.url(file_name)

    def get_success_url(self):
        return self.object.url

    def get_object(self, queryset: QuerySet = None):
        try:
            return super().get_object(queryset)
        except (AttributeError, ObjectDoesNotExist):
            return None


class HTMLTemplateView(BaseTemplateView):
    model = HTMLTemplate
    fields = "__all__"
    template_name = "django_pdf/html_template/index.html"

    def get_context_data(self, **kwargs: Any) -> dict:
        preview_pdf_url = None
        if html_template := self.get_object():
            template_file_content = (
                html_template.template_file.file.read().decode()
            )
            html_template.template_file.file.seek(0)
            preview_pdf_url = self.generate_pdf(html_template)
        elif template_file := self.request.FILES.get("template_file"):
            template_file_content = template_file.read().decode()
        else:
            template = get_template(
                "django_pdf/html_template/base_template.html"
            )
            template_file_content = template.template.source

        return super().get_context_data(**kwargs) | {
            "template_file_content": template_file_content,
            "preview_pdf_url": preview_pdf_url,
        }


class PDFTemplateView(BaseTemplateView):
    model = PDFTemplate
    fields = "__all__"
    template_name = "django_pdf/pdf_template/index.html"

    def get_context_data(self, **kwargs: Any) -> dict:
        template_file_url = None
        preview_pdf_url = None
        if pdf_template := self.get_object():
            template_file_url = pdf_template.template_file.url
            preview_pdf_url = self.generate_pdf(pdf_template)

        return super().get_context_data(**kwargs) | {
            "font_form": FontFamilyForm(),
            "template_file_url": template_file_url,
            "preview_pdf_url": preview_pdf_url,
        }


class TemplateHTMX(TemplatesPermissionMixin, View):
    def get(self, request: HttpRequest, *_: Any, **__: Any) -> HttpResponse:
        template_type = request.GET.get("type")

        if template_type == TemplateType.HTML:
            templates = HTMLTemplate.objects.all()
        else:
            templates = PDFTemplate.objects.all()

        return render(
            request,
            template_name="django_pdf/dashboard/htmx/templates_list.html",
            context={"templates": templates},
        )
