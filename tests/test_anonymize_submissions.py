"""Tests for scripts.anonymize_submissions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.anonymize_submissions import (
    anonymize_directory,
    anonymize_text,
    redact_emails,
    redact_github_usernames,
    redact_name_labels,
    redact_path_names,
    redact_student_ids,
)


class RedactEmailsTests(unittest.TestCase):
    def test_replaces_email_address(self) -> None:
        result = redact_emails("Contact me at john.doe@university.edu for help.")
        self.assertEqual(result, "Contact me at [EMAIL_REDACTED] for help.")

    def test_replaces_multiple_emails(self) -> None:
        text = "From: alice@example.com To: bob@example.org"
        result = redact_emails(text)
        self.assertNotIn("alice@example.com", result)
        self.assertNotIn("bob@example.org", result)
        self.assertEqual(result.count("[EMAIL_REDACTED]"), 2)

    def test_no_false_positive_on_plain_text(self) -> None:
        text = "This has no email address here."
        self.assertEqual(redact_emails(text), text)


class RedactStudentIdsTests(unittest.TestCase):
    def test_replaces_six_digit_id(self) -> None:
        result = redact_student_ids("Student ID: 123456")
        self.assertIn("[STUDENT_ID_REDACTED]", result)
        self.assertNotIn("123456", result)

    def test_replaces_ten_digit_id(self) -> None:
        result = redact_student_ids("SID: 1234567890")
        self.assertIn("[STUDENT_ID_REDACTED]", result)

    def test_does_not_replace_short_numbers(self) -> None:
        text = "Score: 95 out of 100"
        result = redact_student_ids(text)
        self.assertNotIn("[STUDENT_ID_REDACTED]", result)

    def test_does_not_replace_four_digit_year(self) -> None:
        text = "Submitted in 2024."
        result = redact_student_ids(text)
        self.assertNotIn("[STUDENT_ID_REDACTED]", result)


class RedactGithubUsernamesTests(unittest.TestCase):
    def test_replaces_labeled_github_username(self) -> None:
        result = redact_github_usernames("GitHub: johndoe123")
        self.assertIn("[GITHUB_REDACTED]", result)
        self.assertNotIn("johndoe123", result)

    def test_replaces_gh_label(self) -> None:
        result = redact_github_usernames("GH: @alice-dev")
        self.assertIn("[GITHUB_REDACTED]", result)

    def test_no_false_positive_without_label(self) -> None:
        text = "I pushed to the repo."
        result = redact_github_usernames(text)
        self.assertNotIn("[GITHUB_REDACTED]", result)


class RedactNameLabelsTests(unittest.TestCase):
    def test_replaces_name_label(self) -> None:
        result = redact_name_labels("Name: Jane Smith")
        self.assertIn("[NAME_REDACTED]", result)
        self.assertNotIn("Jane Smith", result)

    def test_replaces_student_label(self) -> None:
        result = redact_name_labels("Student: Bob Jones")
        self.assertIn("[NAME_REDACTED]", result)

    def test_replaces_submitted_by_label(self) -> None:
        result = redact_name_labels("Submitted By: Alice Lee")
        self.assertIn("[NAME_REDACTED]", result)

    def test_case_insensitive(self) -> None:
        result = redact_name_labels("NAME: John Doe")
        self.assertIn("[NAME_REDACTED]", result)

    def test_preserves_unrelated_lines(self) -> None:
        text = "Score: 95\nComments: Good work."
        result = redact_name_labels(text)
        self.assertEqual(result, text)


class RedactPathNamesTests(unittest.TestCase):
    def test_replaces_path_with_name_segment(self) -> None:
        result = redact_path_names("/submissions/John_Doe/hw1.py")
        self.assertIn("[PATH_REDACTED]", result)
        self.assertNotIn("John_Doe", result)

    def test_no_false_positive_on_regular_path(self) -> None:
        text = "/home/projects/homework.txt"
        result = redact_path_names(text)
        # "homework" alone is not matched (no underscore/space + two capitalised words)
        self.assertNotIn("[PATH_REDACTED]", result)


class AnonymizeTextTests(unittest.TestCase):
    def test_full_anonymization_pipeline(self) -> None:
        text = (
            "Name: Alice Johnson\n"
            "Email: alice@university.edu\n"
            "GitHub: alice-codes\n"
            "Student ID: 1234567\n"
            "File: /submissions/Alice_Johnson/solution.py\n"
        )
        result = anonymize_text(text)
        self.assertNotIn("Alice Johnson", result)
        self.assertNotIn("alice@university.edu", result)
        self.assertNotIn("alice-codes", result)
        self.assertNotIn("1234567", result)
        self.assertIn("[NAME_REDACTED]", result)
        self.assertIn("[EMAIL_REDACTED]", result)
        self.assertIn("[STUDENT_ID_REDACTED]", result)


class AnonymizeDirectoryTests(unittest.TestCase):
    def test_processes_text_files_and_preserves_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            input_dir = base / "input"
            output_dir = base / "output"

            (input_dir / "subdir").mkdir(parents=True)
            (input_dir / "subdir" / "file.txt").write_text(
                "Name: Bob Smith\nEmail: bob@example.com", encoding="utf-8"
            )

            anonymized, copied = anonymize_directory(input_dir, output_dir)

            self.assertEqual(anonymized, 1)
            self.assertEqual(copied, 0)
            result = (output_dir / "subdir" / "file.txt").read_text(encoding="utf-8")
            self.assertNotIn("Bob Smith", result)
            self.assertNotIn("bob@example.com", result)

    def test_copies_non_text_files_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            input_dir = base / "input"
            output_dir = base / "output"
            input_dir.mkdir()

            binary_content = b"\x00\x01\x02\x03"
            (input_dir / "data.bin").write_bytes(binary_content)

            anonymized, copied = anonymize_directory(input_dir, output_dir)

            self.assertEqual(anonymized, 0)
            self.assertEqual(copied, 1)
            self.assertEqual((output_dir / "data.bin").read_bytes(), binary_content)

    def test_raises_if_input_dir_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            anonymize_directory(Path("/nonexistent/path"), Path("/tmp/out"))


if __name__ == "__main__":
    unittest.main()
