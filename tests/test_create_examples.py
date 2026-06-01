"""Tests for scripts.create_examples helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.create_examples import build_records, infer_category, split_into_chunks


class CreateExamplesTests(unittest.TestCase):
    def test_infer_category_from_top_level_directory(self) -> None:
        cleaned_dir = Path("cleaned")
        file_path = Path("cleaned/rubrics/week1.txt")
        self.assertEqual(infer_category(file_path, cleaned_dir), "rubric")

    def test_split_into_chunks_handles_empty_text(self) -> None:
        self.assertEqual(split_into_chunks("   \n\n  "), [])

    def test_split_into_chunks_uses_word_boundaries(self) -> None:
        text = "alpha beta gamma delta"
        chunks = split_into_chunks(text, max_chars=11)
        self.assertEqual(chunks, ["alpha beta", "gamma delta"])

    def test_split_into_chunks_keeps_very_long_word_intact(self) -> None:
        long_word = "x" * 40
        chunks = split_into_chunks(long_word, max_chars=10)
        self.assertEqual(chunks, [long_word])

    def test_build_records_sets_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cleaned_dir = Path(tmp_dir) / "cleaned"
            file_path = cleaned_dir / "assignments" / "week1.txt"
            file_path.parent.mkdir(parents=True)
            file_path.write_text("Read chapter one.\n\nSubmit summary.", encoding="utf-8")

            records = build_records(file_path=file_path, cleaned_dir=cleaned_dir, max_chars=100)

            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["category"], "assignment")
            self.assertIn("assignment requirements", record["instruction"])
            self.assertEqual(record["source_file"], "assignments/week1.txt")
            self.assertEqual(record["output"], "")
            self.assertIn("Read chapter one.", record["input"])


if __name__ == "__main__":
    unittest.main()
