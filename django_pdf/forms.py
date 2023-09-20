from django import forms
from django.db import models
from reportlab.pdfgen import canvas

from django_pdf.models import SUPPORTED_FONTS, HTMLTemplate


class TemplateType(models.TextChoices):
    HTML = "html", "HTML Template"
    PDF = "pdf", "PDF Template"


class TemplateTypeForm(forms.Form):
    type = forms.ChoiceField(
        choices=TemplateType.choices,
    )


class FontFamilyForm(forms.Form):
    font_family = forms.ChoiceField(
        choices=[
            (font_name, font_name) for font_name in SUPPORTED_FONTS.keys()
        ]
    )
