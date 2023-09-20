from abc import ABC, abstractmethod
from enum import Enum
from io import BytesIO
from typing import Any, Dict, Tuple, Type, TypedDict

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.shortcuts import render
from django.template import Engine, Context
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from typeguard import check_type
from xhtml2pdf import pisa


class HTMLContextSchemaValue(TypedDict):
    required: bool


class PDFContextSchemaValue(TypedDict):
    required: bool
    font_family: str
    font_size_px: int


HTMLContextSchema = Dict[str, HTMLContextSchemaValue]
PDFContextSchema = Dict[str, PDFContextSchemaValue]

SUPPORTED_FONTS = {
    'Arial, Helvetica, sans-serif': 'Arial',
    'Courier New, Courier, monospace': 'Courier',
    'Helvetica, Arial, sans-serif': 'Helvetica',
    'Symbol': 'Symbol',
    'Times New Roman, Times, serif': 'Times-Roman',
    'ZapfDingbats': 'ZapfDingbats',
}


class BaseTemplate(models.Model):
    PDF_TEMPLATE_DIR = getattr(settings, "PDF_TEMPLATE_DIR", "django_pdf_files")
    context_schema = models.JSONField()
    example_context = models.JSONField()
    name = models.CharField(unique=True, max_length=255)

    def validate_context(self, context: Dict[str, Any]) -> None:
        errors = []
        for key, schema_value in self.context_schema.items():
            if not context.get(key) and schema_value["required"]:
                errors.append(f"{key} is a required field")
        if errors:
            raise ValueError(
                f"The context dictionary has the following errors: {errors}",
            )

    def generate(self, context: Dict[str, Any]) -> BytesIO:
        raise NotImplemented

    class Meta:
        abstract = True


class HTMLTemplate(BaseTemplate):
    template_file = models.FileField(
        upload_to=BaseTemplate.PDF_TEMPLATE_DIR,
        validators=[FileExtensionValidator(allowed_extensions=["html"])],
    )

    def generate(self, context: Dict[str, Any]) -> BytesIO:
        self.validate_context(context)
        html = self.render_html(context=context)
        pdf_buffer = BytesIO()
        pisa.CreatePDF(html, dest=pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer

    def render_html(self, context: Dict[str, Any]) -> str:
        template_str = self.template_file.file.read().decode()
        current_engine = Engine.get_default()
        template = current_engine.from_string(template_str)
        return template.render(Context(context))

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not check_type(self.context_schema, HTMLContextSchema):
            raise ValidationError("The context_schema is incorrect")
        super().save(*args, **kwargs)

    @property
    def url(self) -> None | str:
        if self.pk:
            return reverse(
                "django_pdf:update-html-template", args=(self.pk,)
            )
        return None

    class Meta:
        verbose_name = "HTML Template"


class PDFTemplate(BaseTemplate):

    template_file = models.FileField(
        upload_to=BaseTemplate.PDF_TEMPLATE_DIR,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )

    def generate(self, context: Dict[str, Any]) -> BytesIO:
        self.validate_context(context)
        pdf_buffer = BytesIO()
        return pdf_buffer

    @property
    def url(self) -> None | str:
        if self.pk:
            return reverse(
                "django_pdf:update-pdf-template", args=(self.pk,)
            )
        return None

    class Meta:
        verbose_name = "PDF Template"
