from django.contrib import admin

from django_pdf.models import HTMLTemplate, PDFTemplate


@admin.register(HTMLTemplate)
class HTMLTemplateAmin(admin.ModelAdmin):
    pass


@admin.register(PDFTemplate)
class PDFTemplateAmin(admin.ModelAdmin):
    pass
