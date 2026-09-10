"""User settings translated to Marker's configuration format."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

VALID_MODES = ("balanced", "fast")
DEFAULT_BATCH_SIZE = 32


def _output_dir() -> Path:
    return Path(os.environ.get("PDF2MD_OUTPUT_DIR", "files"))


def detect_default_mode() -> str:
    """Use balanced mode on CUDA and fast mode everywhere else."""
    try:
        import torch

        return "balanced" if torch.cuda.is_available() else "fast"
    except ImportError:
        return "fast"


@dataclass(frozen=True)
class ConverterSettings:
    """Options that affect document conversion."""

    output_dir: Path = field(default_factory=_output_dir)
    save_images: bool = True
    page_range: str | None = None
    languages: list[str] | None = None
    force_ocr: bool = False
    mode: str | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    resume: bool = True

    def __post_init__(self) -> None:
        if self.mode is not None and self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")

    @property
    def effective_mode(self) -> str:
        return self.mode or detect_default_mode()

    def to_marker_config(self, page_range: str | None = None) -> dict:
        """Build the configuration consumed by Marker's ConfigParser."""
        config: dict = {"output_format": "markdown"}
        if self.effective_mode == "balanced":
            config["format_lines"] = True
        selected_pages = self.page_range if page_range is None else page_range
        if selected_pages:
            config["page_range"] = selected_pages
        if self.languages:
            config["languages"] = ",".join(self.languages)
        if self.force_ocr:
            config["force_ocr"] = True
        return config
