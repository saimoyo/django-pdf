import uuid
from datetime import datetime
from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, \
    PermissionRequiredMixin
from django.core.files.storage import default_storage
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.urls import reverse
from django.utils.html import escape
from django.views import View
from django.views.generic import TemplateView, UpdateView

from django_pdf.forms import TemplateTypeForm, TemplateType, FontFamilyForm
from django_pdf.models import HTMLTemplate, PDFTemplate
from django.core.exceptions import ObjectDoesNotExist


class _TemplatesPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = getattr(settings, "PDF_PERMISSIONS", [])


class DashboardView(_TemplatesPermissionMixin, TemplateView):
    permission_required = getattr(settings, "PDF_PERMISSIONS", [])
    template_name = "django_pdf/dashboard/index.html"

    def get_context_data(self, **kwargs: Any) -> dict:
        return super().get_context_data(**kwargs) | {
            "type_form": TemplateTypeForm()
        }


class _CreateOrUpdateView(_TemplatesPermissionMixin, UpdateView):
    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except (AttributeError, ObjectDoesNotExist):
            return None


class HTMLTemplateView(_CreateOrUpdateView):
    model = HTMLTemplate
    fields = "__all__"
    template_name = "django_pdf/html_template/index.html"

    def get_context_data(self, **kwargs: Any) -> dict:
        pdf_url = None
        if html_template := self.get_object():
            template_file_content = html_template.template_file.file.read().decode()
            html_template.template_file.file.seek(0)
            pdf_buffer = html_template.generate(html_template.example_context)
            current_hour = datetime.now().hour
            file_name = f"{HTMLTemplate.PDF_TEMPLATE_DIR}/temp/{html_template.name}_{current_hour}.pdf"
            default_storage.delete(file_name)
            default_storage.save(file_name, pdf_buffer)
            pdf_url = default_storage.url(file_name)

        elif template_file := self.request.FILES.get("template_file"):
            template_file_content = template_file.read().decode()
        else:
            template = get_template(
                "django_pdf/html_template/base_template.html"
            )
            template_file_content = template.template.source

        return super().get_context_data(**kwargs) | {
            "template_file_content": template_file_content,
            "pdf_url": pdf_url
        }

    def get_success_url(self):
        return self.object.url


class PDFTemplateView(_CreateOrUpdateView):
    model = PDFTemplate
    fields = "__all__"
    template_name = "django_pdf/pdf_template/index.html"

    def get_context_data(self, **kwargs: Any) -> dict:
        pdf_url = None
        if pdf_template := self.get_object():
            pdf_url = pdf_template.template_file.url

        return super().get_context_data(**kwargs) | {
            "font_form": FontFamilyForm(),
            "pdf_url": pdf_url,
        }

    def get_success_url(self):
        self.form_invalid
        return self.object.url


class TemplateHTMX(_TemplatesPermissionMixin, View):
    def get(self, request: HttpRequest, *_: Any, **__: Any) -> HttpResponse:
        template_type = request.GET.get("type")

        if template_type == TemplateType.HTML:
            templates = HTMLTemplate.objects.all()
        else:
            templates = PDFTemplate.objects.all()

        return render(
            request,
            template_name="django_pdf/dashboard/htmx/templates_list.html",
            context={"templates": templates}
        )
