"""Tests for scripts.create_grading_packet."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.create_grading_packet import PACKET_FILES, create_grading_packet


class CreateGradingPacketTests(unittest.TestCase):
    def test_creates_all_packet_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            # Create the PACKET_ROOT parent so the script can mkdir inside it.
            (base / "processed").mkdir()

            packet_dir = create_grading_packet(course="databases", assignment="assignment-01", base_dir=base)

            self.assertTrue(packet_dir.is_dir())
            for filename in PACKET_FILES:
                self.assertTrue(
                    (packet_dir / filename).is_file(),
                    msg=f"Expected {filename} to exist in packet",
                )

    def test_packet_directory_name_is_course_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "processed").mkdir()

            packet_dir = create_grading_packet(course="cs101", assignment="hw-02", base_dir=base)

            self.assertEqual(packet_dir.name, "cs101-hw-02")

    def test_stub_files_contain_placeholder_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "processed").mkdir()

            packet_dir = create_grading_packet(course="math", assignment="quiz-01", base_dir=base)

            assignment_content = (packet_dir / "assignment.md").read_text(encoding="utf-8")
            self.assertIn("<!--", assignment_content)

    def test_raises_if_packet_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "processed").mkdir()

            create_grading_packet(course="cs101", assignment="hw-01", base_dir=base)

            with self.assertRaises(FileExistsError):
                create_grading_packet(course="cs101", assignment="hw-01", base_dir=base)

    def test_copies_raw_source_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "processed").mkdir()

            # Place a matching raw assignment file.
            raw_assignments = base / "raw" / "assignments" / "databases"
            raw_assignments.mkdir(parents=True)
            expected_content = "# Real Assignment\n\nDo this task.\n"
            (raw_assignments / "assignment-01.md").write_text(expected_content, encoding="utf-8")

            packet_dir = create_grading_packet(course="databases", assignment="assignment-01", base_dir=base)

            actual = (packet_dir / "assignment.md").read_text(encoding="utf-8")
            self.assertEqual(actual, expected_content)


if __name__ == "__main__":
    unittest.main()
