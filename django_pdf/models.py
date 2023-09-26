from abc import ABC, abstractmethod
from enum import Enum
from io import BytesIO
from typing import Any, Dict, Tuple, Type, TypedDict

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.shortcuts import render
from django.template import Context, Engine
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
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

# TODO: Add support for custom fonts
SUPPORTED_FONTS = {
    "Helvetica, Arial, sans-serif": "Helvetica",
    "Symbol": "Symbol",
    "ZapfDingbats": "ZapfDingbats",
}


class BaseTemplate(models.Model):
    PDF_TEMPLATE_DIR = getattr(
        settings, "PDF_TEMPLATE_DIR", "django_pdf_files"
    )
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
            return reverse("django_pdf:update-html-template", args=(self.pk,))
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
        # Read the existing PDF
        self.template_file.file.seek(0)
        pdf_reader = PdfReader(self.template_file.file)
        self.template_file.file.seek(0)

        pdf_writer = PdfWriter()

        # Get the page size from the existing PDF (assuming all pages have the same size)
        first_page = pdf_reader.pages[0]
        page_width = first_page.mediabox.width
        page_height = first_page.mediabox.height

        # Create a canvas for adding text to the new PDF with the same page size
        packets = {}

        # Add each text element to the canvas
        for variable, value in context.items():
            if not (variable_schema := self.context_schema[variable]):
                continue
            page_index = int(variable_schema["y_px"])
            if not (page_packets := packets.get(page_index)):
                page_packets = []
                packets[page_index] = page_packets
            packet = BytesIO()
            page_packets.append(packet)
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))
            x_point = variable_schema["x_px"] * page_width
            y_point = (1 - variable_schema["y_px"] % 1) * page_height
            font_family = SUPPORTED_FONTS.get(
                variable_schema["font_family"], "Helvetica"
            )
            font_size = pixels_to_points(variable_schema["font_size_px"])
            c.setFont(font_family, font_size)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(x_point, y_point, value)
            c.showPage()
            c.save()

        # Move the buffer's position to the beginning

        # Merge the content of the existing PDF with the new PDF (with added text)
        for page_num, page in enumerate(pdf_reader.pages):
            for packet in packets.get(page_num, []):
                packet.seek(0)
                new_pdf = PdfReader(packet)
                page.merge_page(new_pdf.pages[0])
            pdf_writer.add_page(page)

        pdf_buffer = BytesIO()
        pdf_writer.write(pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer

    @property
    def url(self) -> None | str:
        if self.pk:
            return reverse("django_pdf:update-pdf-template", args=(self.pk,))
        return None

    class Meta:
        verbose_name = "PDF Template"


def pixels_to_points(pixels, dpi=96):
    inches = pixels / dpi
    points = inches * 72
    return points
