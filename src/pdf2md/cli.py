"""Command-line interface for the document converter."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pdf2md.config import DEFAULT_BATCH_SIZE, ConverterSettings
from pdf2md.converter import PdfToMarkdownConverter
from pdf2md.exceptions import PdfConversionError

logger = logging.getLogger("pdf2md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="Convert a document or image to Markdown using Marker.",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Input file: PDF, Office, EPUB, HTML, or image",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .md file (default: <output-dir>/<source>/<source>.md)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Root output directory (default: ./files or PDF2MD_OUTPUT_DIR)",
    )
    parser.add_argument(
        "--mode",
        choices=("balanced", "fast"),
        help="Quality mode (default: balanced on CUDA, fast otherwise)",
    )
    parser.add_argument(
        "--pages",
        help='PDF pages, 0-indexed; for example "0-4,7"',
    )
    parser.add_argument(
        "--langs",
        help='Comma-separated OCR languages; for example "en,de"',
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Re-OCR every page",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help=f"Pages per PDF batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Do not save extracted images",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Convert every PDF batch again instead of reusing finished ones",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    options = {
        "save_images": not args.no_images,
        "page_range": args.pages,
        "languages": args.langs.split(",") if args.langs else None,
        "force_ocr": args.force_ocr,
        "mode": args.mode,
        "resume": not args.no_resume,
    }
    if args.output_dir is not None:
        options["output_dir"] = args.output_dir
    if args.batch_size is not None:
        options["batch_size"] = args.batch_size

    try:
        settings = ConverterSettings(**options)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    try:
        result = PdfToMarkdownConverter(settings).convert(args.source, args.output)
    except PdfConversionError as exc:
        logger.error("%s", exc)
        return 1

    print(result.markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
