"""Tests for scripts.clean_text helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.clean_text import clean_raw_documents, normalize_whitespace, output_path_for


class CleanTextTests(unittest.TestCase):
    def test_normalize_whitespace_collapses_blank_lines(self) -> None:
        raw = "Line 1  \n\n\nLine 2\r\n\r\nLine 3   "
        self.assertEqual(normalize_whitespace(raw), "Line 1\n\nLine 2\n\nLine 3\n")

    def test_output_path_for_preserves_relative_structure(self) -> None:
        raw_dir = Path("raw")
        cleaned_dir = Path("cleaned")
        source = Path("raw/syllabi/week1/intro.md")
        target = output_path_for(source, raw_dir=raw_dir, cleaned_dir=cleaned_dir)
        self.assertEqual(target, Path("cleaned/syllabi/week1/intro.txt"))

    def test_clean_raw_documents_processes_supported_and_skips_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_dir = base / "raw"
            cleaned_dir = base / "cleaned"
            (raw_dir / "syllabi").mkdir(parents=True)
            (raw_dir / "syllabi" / "week1.md").write_text("Hello\n\n\nWorld", encoding="utf-8")
            (raw_dir / "syllabi" / "ignore.bin").write_bytes(b"\x00\x01")

            processed, skipped = clean_raw_documents(raw_dir=raw_dir, cleaned_dir=cleaned_dir)

            self.assertEqual(processed, 1)
            self.assertEqual(skipped, 1)
            output = (cleaned_dir / "syllabi" / "week1.txt").read_text(encoding="utf-8")
            self.assertEqual(output, "Hello\n\nWorld\n")


if __name__ == "__main__":
    unittest.main()
