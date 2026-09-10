"""Convert documents to Markdown with Marker."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pdf2md.config import ConverterSettings
from pdf2md.exceptions import ConversionFailedError, InvalidInputError

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".epub", ".html",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".tiff",
}

CACHE_DIR_NAME = ".batches"
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class ConversionResult:
    """Files produced by one conversion."""

    source: Path
    markdown_path: Path
    image_paths: list[Path] = field(default_factory=list)

    @property
    def markdown(self) -> str:
        return self.markdown_path.read_text(encoding="utf-8")


class PdfToMarkdownConverter:
    """Convert supported files to Markdown with one reusable Marker instance."""

    def __init__(self, settings: ConverterSettings | None = None) -> None:
        self.settings = settings or ConverterSettings()
        self._models = None

    def convert(
        self,
        pdf_path: str | Path,
        output_path: str | Path | None = None,
    ) -> ConversionResult:
        source = self._validate_input(Path(pdf_path))
        target = Path(output_path) if output_path else self._default_target(source)

        target.parent.mkdir(parents=True, exist_ok=True)

        if source.suffix.lower() == ".pdf":
            markdown, image_paths = self._convert_pdf(source, target.parent)
        else:
            markdown, images = self._run_marker(source, "")
            image_paths = self._save_images(images, target.parent)

        target.write_text(markdown, encoding="utf-8")

        logger.info(
            "Wrote %s (%d chars, %d images)", target, len(markdown), len(image_paths)
        )
        return ConversionResult(source, target, image_paths)

    def _default_target(self, source: Path) -> Path:
        return self.settings.output_dir / source.stem / f"{source.stem}.md"

    @staticmethod
    def _validate_input(source: Path) -> Path:
        if not source.is_file():
            raise InvalidInputError(f"File not found: {source}")
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise InvalidInputError(
                f"Unsupported file type {source.suffix!r}; expected one of {supported}"
            )
        return source

    def _convert_pdf(self, source: Path, directory: Path) -> tuple[str, list[Path]]:
        """Convert a PDF batch by batch, reusing batches an earlier run finished."""
        batches = self._pdf_batches(source)
        cache = directory / CACHE_DIR_NAME
        completed = self._completed_batches(cache, source)

        parts: list[str] = []
        image_paths: list[Path] = []
        for number, pages in enumerate(batches, start=1):
            name = f"pages_{pages[0]:04d}-{pages[-1]:04d}.md"
            entry = completed.get(name)

            if entry is not None:
                logger.info(
                    "Skipping batch %d/%d (pages %d-%d, already converted)",
                    number, len(batches), pages[0], pages[-1],
                )
                parts.append((cache / name).read_text(encoding="utf-8"))
                image_paths.extend(
                    directory / image for image in entry.get("images", [])
                )
                continue

            logger.info(
                "Converting batch %d/%d (pages %d-%d)",
                number, len(batches), pages[0], pages[-1],
            )
            markdown, images = self._run_marker(source, ",".join(map(str, pages)))
            saved = self._save_images(images, directory)

            cache.mkdir(parents=True, exist_ok=True)
            (cache / name).write_text(markdown, encoding="utf-8")
            completed[name] = {
                "file": name,
                "pages": pages,
                "images": [path.name for path in saved],
            }
            self._write_manifest(cache, source, completed)

            parts.append(markdown)
            image_paths.extend(saved)

        return self._merge(parts), image_paths

    def _pdf_batches(self, source: Path) -> list[list[int]]:
        import pypdfium2
        from marker.util import parse_range_str

        document = pypdfium2.PdfDocument(str(source))
        try:
            page_count = len(document)
        finally:
            document.close()

        try:
            pages = (
                parse_range_str(self.settings.page_range)
                if self.settings.page_range
                else list(range(page_count))
            )
        except ValueError:
            raise InvalidInputError(
                f"Invalid page range: {self.settings.page_range!r}"
            ) from None

        if not pages or min(pages) < 0 or max(pages) >= page_count:
            raise InvalidInputError(
                f"Page range must be between 0 and {page_count - 1}"
            )

        size = self.settings.batch_size
        return [pages[start : start + size] for start in range(0, len(pages), size)]

    def _fingerprint(self, source: Path) -> dict:
        """Identify the source and the settings a cached batch was produced with."""
        stat = source.stat()
        return {
            "source": {
                "name": source.name,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            },
            "settings": {
                "mode": self.settings.effective_mode,
                "page_range": self.settings.page_range,
                "languages": (
                    ",".join(self.settings.languages)
                    if self.settings.languages
                    else None
                ),
                "force_ocr": self.settings.force_ocr,
                "batch_size": self.settings.batch_size,
            },
        }

    def _completed_batches(self, cache: Path, source: Path) -> dict[str, dict]:
        """Batches an earlier run of this same source and settings already wrote."""
        manifest = cache / MANIFEST_NAME
        if not self.settings.resume or not manifest.is_file():
            return {}
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("Ignoring unreadable manifest %s", manifest)
            return {}
        if data.get("fingerprint") != self._fingerprint(source):
            logger.info("Source or settings changed; converting every batch again")
            return {}
        return {
            entry["file"]: entry
            for entry in data.get("batches", [])
            if (cache / entry["file"]).is_file()
        }

    def _write_manifest(
        self, cache: Path, source: Path, completed: dict[str, dict]
    ) -> None:
        payload = {
            "fingerprint": self._fingerprint(source),
            "batches": list(completed.values()),
        }
        (cache / MANIFEST_NAME).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    @staticmethod
    def _merge(parts: list[str]) -> str:
        if len(parts) <= 1:
            return parts[0] if parts else ""
        return "\n\n".join(part.strip("\n") for part in parts)

    def _get_models(self):
        if self._models is None:
            from marker.models import create_model_dict

            logger.info("Loading Marker models (first call only, may take a while)...")
            self._models = create_model_dict()
        return self._models

    def _run_marker(self, source: Path, page_range: str) -> tuple[str, dict]:
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.output import text_from_rendered

        try:
            parser = ConfigParser(self.settings.to_marker_config(page_range))
            converter = PdfConverter(
                artifact_dict=self._get_models(),
                config=parser.generate_config_dict(),
                processor_list=parser.get_processors(),
                renderer=parser.get_renderer(),
            )
            rendered = converter(str(source))
            markdown, _, images = text_from_rendered(rendered)
            return markdown, images
        except Exception as exc:
            raise ConversionFailedError(f"Marker failed on {source}: {exc}") from exc

    def _save_images(self, images: dict, directory: Path) -> list[Path]:
        if not self.settings.save_images:
            return []

        paths: list[Path] = []
        for name, image in images.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
            paths.append(path)
        return paths
