"""Utilities for cleaning raw source documents into normalized text files."""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}


def normalize_whitespace(text: str) -> str:
    """Normalize line endings, trim trailing spaces, and collapse blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n" if text.strip() else ""


def extract_text(file_path: Path) -> str:
    """Extract readable text from a supported file type."""
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        doc = Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    if suffix == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


def iter_raw_files(raw_dir: Path) -> list[Path]:
    """Return all files beneath raw_dir recursively."""
    return [path for path in raw_dir.rglob("*") if path.is_file()]


def output_path_for(file_path: Path, raw_dir: Path, cleaned_dir: Path) -> Path:
    """Map an input file path under raw_dir to a .txt output under cleaned_dir."""
    rel_path = file_path.relative_to(raw_dir)
    return (cleaned_dir / rel_path).with_suffix(".txt")


def clean_raw_documents(raw_dir: Path, cleaned_dir: Path) -> tuple[int, int]:
    """Clean all supported documents from raw_dir into cleaned_dir.

    Returns:
        A tuple of (processed_count, skipped_count).
    """
    processed = 0
    skipped = 0

    for file_path in iter_raw_files(raw_dir):
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            skipped += 1
            logging.warning("Skipping unsupported file: %s", file_path)
            continue

        output_path = output_path_for(file_path, raw_dir, cleaned_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cleaned_text = normalize_whitespace(extract_text(file_path))
        output_path.write_text(cleaned_text, encoding="utf-8")
        processed += 1

    return processed, skipped


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Clean raw documents into plain text.")
    parser.add_argument("--raw-dir", default="raw", help="Input directory containing source documents")
    parser.add_argument("--cleaned-dir", default="cleaned", help="Output directory for cleaned text")
    parser.add_argument("--log-level", default="INFO", help="Logging level (e.g., INFO, DEBUG)")
    return parser.parse_args()


def main() -> None:
    """Run the cleaning pipeline from CLI arguments."""
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    raw_dir = Path(args.raw_dir)
    cleaned_dir = Path(args.cleaned_dir)

    processed, skipped = clean_raw_documents(raw_dir=raw_dir, cleaned_dir=cleaned_dir)
    logging.info("Completed cleaning. Processed=%s Skipped=%s", processed, skipped)


if __name__ == "__main__":
    main()
