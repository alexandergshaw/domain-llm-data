"""Tests for scripts.validate_grading_examples."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_grading_examples import validate_file, validate_record


def _make_valid_record() -> dict:
    return {
        "instruction": "Grade this assignment using the provided rubric.",
        "input": {
            "course": "databases",
            "assignment_id": "assignment-01",
            "assignment_prompt": "Design a schema.",
            "rubric": "Correctness: 50 pts",
            "student_submission": "CREATE TABLE ...",
        },
        "output": {
            "score": 85,
            "points_possible": 100,
            "rubric_breakdown": [
                {"criterion": "Correctness", "points_awarded": 45, "points_possible": 50, "feedback": "Good."}
            ],
            "summary_feedback": "Well done.",
            "revision_priorities": ["Add indexes"],
            "flags": [],
        },
        "category": "grading",
    }


class ValidateRecordTests(unittest.TestCase):
    def test_valid_record_produces_no_errors(self) -> None:
        record = _make_valid_record()
        errors = validate_record(record, line_number=1)
        self.assertEqual(errors, [])

    def test_missing_top_level_instruction(self) -> None:
        record = _make_valid_record()
        del record["instruction"]
        errors = validate_record(record, line_number=1)
        self.assertTrue(any("instruction" in e for e in errors))

    def test_missing_input_field_course(self) -> None:
        record = _make_valid_record()
        del record["input"]["course"]
        errors = validate_record(record, line_number=1)
        self.assertTrue(any("course" in e for e in errors))

    def test_missing_output_field_score(self) -> None:
        record = _make_valid_record()
        del record["output"]["score"]
        errors = validate_record(record, line_number=1)
        self.assertTrue(any("score" in e for e in errors))

    def test_score_must_be_numeric(self) -> None:
        record = _make_valid_record()
        record["output"]["score"] = "eighty-five"
        errors = validate_record(record, line_number=2)
        self.assertTrue(any("score" in e and "numeric" in e for e in errors))

    def test_points_possible_must_be_numeric(self) -> None:
        record = _make_valid_record()
        record["output"]["points_possible"] = "one hundred"
        errors = validate_record(record, line_number=3)
        self.assertTrue(any("points_possible" in e and "numeric" in e for e in errors))

    def test_rubric_breakdown_must_be_list(self) -> None:
        record = _make_valid_record()
        record["output"]["rubric_breakdown"] = "not a list"
        errors = validate_record(record, line_number=4)
        self.assertTrue(any("rubric_breakdown" in e and "list" in e for e in errors))

    def test_float_score_is_valid(self) -> None:
        record = _make_valid_record()
        record["output"]["score"] = 87.5
        errors = validate_record(record, line_number=1)
        self.assertEqual(errors, [])

    def test_input_must_be_dict(self) -> None:
        record = _make_valid_record()
        record["input"] = "a string"
        errors = validate_record(record, line_number=1)
        self.assertTrue(any("input" in e for e in errors))


class ValidateFileTests(unittest.TestCase):
    def _write_jsonl(self, tmp_dir: Path, lines: list[str]) -> Path:
        path = tmp_dir / "examples.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_valid_file_returns_zero_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_jsonl(
                Path(tmp_dir), [json.dumps(_make_valid_record())]
            )
            total, valid, errors = validate_file(path)
            self.assertEqual(total, 1)
            self.assertEqual(valid, 1)
            self.assertEqual(errors, [])

    def test_invalid_json_line_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_jsonl(Path(tmp_dir), ["{not valid json"])
            total, valid, errors = validate_file(path)
            self.assertEqual(total, 1)
            self.assertTrue(any("invalid JSON" in e for e in errors))

    def test_blank_lines_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_jsonl(
                Path(tmp_dir),
                ["", json.dumps(_make_valid_record()), ""],
            )
            total, valid, errors = validate_file(path)
            self.assertEqual(total, 1)
            self.assertEqual(errors, [])

    def test_missing_field_makes_record_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad = _make_valid_record()
            del bad["category"]
            path = self._write_jsonl(Path(tmp_dir), [json.dumps(bad)])
            total, valid, errors = validate_file(path)
            self.assertEqual(total, 1)
            self.assertEqual(valid, 0)
            self.assertTrue(any("category" in e for e in errors))

    def test_raises_if_file_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            validate_file(Path("/nonexistent/file.jsonl"))

    def test_multiple_records_mixed_validity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            good = json.dumps(_make_valid_record())
            bad = _make_valid_record()
            del bad["output"]["score"]
            bad_str = json.dumps(bad)
            path = self._write_jsonl(Path(tmp_dir), [good, bad_str])
            total, valid, errors = validate_file(path)
            self.assertEqual(total, 2)
            self.assertEqual(valid, 1)
            self.assertTrue(len(errors) > 0)


if __name__ == "__main__":
    unittest.main()
