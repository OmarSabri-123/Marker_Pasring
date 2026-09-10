"""PDF-to-Markdown conversion built on the Marker library.

Public API:
    from pdf2md import PdfToMarkdownConverter, ConverterSettings, ConversionResult
"""

from pdf2md.config import ConverterSettings
from pdf2md.converter import ConversionResult, PdfToMarkdownConverter
from pdf2md.exceptions import (
    ConversionFailedError,
    InvalidInputError,
    PdfConversionError,
)

__all__ = [
    "ConversionFailedError",
    "ConversionResult",
    "ConverterSettings",
    "InvalidInputError",
    "PdfConversionError",
    "PdfToMarkdownConverter",
]
