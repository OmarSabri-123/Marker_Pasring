"""Domain exceptions for the PDF-to-Markdown feature."""


class PdfConversionError(Exception):
    """Base class for every error raised by this package."""


class InvalidInputError(PdfConversionError):
    """The input path is missing, not a file, or not a PDF."""


class ConversionFailedError(PdfConversionError):
    """Marker failed while processing the document."""
