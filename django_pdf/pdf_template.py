from abc import ABC, abstractmethod
from enum import Enum
from io import BytesIO
from typing import Any, Dict, Tuple, Type, TypedDict

from django.template.loader import get_template
from xhtml2pdf import pisa


class ContextSchemaValue(TypedDict):
    required: bool
    type: Type


ContextSchema = Dict[str, ContextSchemaValue]


class PageSizeInMM(Enum):
    """Common page sizes in millimeters"""

    A0 = (841, 1189)
    A1 = (594, 841)
    A2 = (420, 594)
    A3 = (297, 420)
    A4 = (210, 297)
    A5 = (148.5, 210)
    A6 = (105, 148)
    B0 = (1000, 1414)
    B1 = (707, 1000)
    B2 = (500, 707)
    B3 = (353, 500)
    B4 = (250, 353)
    B5 = (176, 250)
    Legal = (8.5, 14)
    Letter = (8.5, 11)


class PDFTemplate(ABC):
    landscape: bool = False
    margin_bottom_mm: int = 10
    margin_left_mm: int = 10
    margin_right_mm: int = 10
    margin_top_mm: int = 10
    page_size_mm: Tuple[int, int] = PageSizeInMM.A4.value

    @property
    @abstractmethod
    def context_schema(self) -> ContextSchema:
        """
        This defines the structure and expectations of the context dictionary
        that should be provided when generating a PDF using this template.

        Returns:
            ContextSchema: A dictionary where each key represents a context
                variable, and the associated value is a ContextSchemaValue
                that specifies whether the variable is required and its
                expected data type.

        Example:
            return {
                'title': {
                    'required': True,  # Title is a required context variable
                    'type': str,        # Title should be a string
                },
                'content': {
                    'required': False,  # Content is optional
                    'type': str,        # Content should be a string
                },
                'date': {
                    'required': True,   # Date is required
                    'type': datetime.date,  # Date should be a date object
                },
            }
        """

    @property
    @abstractmethod
    def template_name(self) -> str:
        pass

    def get_page_size_string(self):
        page_size_mm = self.page_size_mm
        width = page_size_mm[1] if self.landscape else page_size_mm[0]
        height = page_size_mm[0] if self.landscape else page_size_mm[1]
        return f"{width}mm {height}mm"

    def get_page_options(self, **_: Any) -> Dict[str, Any]:
        return {
            "page_size": self.get_page_size_string(),
            "margin_top": self.margin_top_mm,
            "margin_right": self.margin_right_mm,
            "margin_bottom": self.margin_bottom_mm,
            "margin_left": self.margin_left_mm,
        }

    def generate(self, context: Dict[str, Any]) -> BytesIO:
        self.validate_context(context)
        page_options = self.get_page_options()
        html = self.render_html(context=context | page_options)
        pdf_buffer = BytesIO()
        pisa.CreatePDF(html, dest=pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer

    def render_html(self, context: Dict[str, Any]) -> str:
        template = get_template(self.template_name)
        return template.render(context)

    def validate_context(self, context: Dict[str, Any]) -> None:
        errors = []
        for key, schema_value in self.context_schema.items():
            expected_type = schema_value["type"]
            if value := context.get(key):
                if not isinstance(value, expected_type):
                    errors.append(
                        f"{key} must be a {expected_type}, not a {type(value)}"
                    )
            elif schema_value["required"]:
                errors.append(f"{key} is a required field")
        if errors:
            raise ValueError(
                f"The context dictionary has the following errors: {errors}",
            )
