"""Generate a complete grading packet folder for a new assignment."""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path


RAW_ASSIGNMENTS = Path("raw/assignments")
RAW_RUBRICS = Path("raw/rubrics")
RAW_POLICIES = Path("raw/policies")
RAW_EXPECTED = Path("raw/expected-solutions")
RAW_FEEDBACK = Path("raw/instructor-feedback")
PACKET_ROOT = Path("processed/grading-packets")

PACKET_FILES = [
    "assignment.md",
    "rubric.md",
    "expected-solution.md",
    "common-mistakes.md",
    "policies.md",
    "sample-feedback.md",
]

# Maps each packet file to the raw source directory to search first.
_RAW_LOOKUP: dict[str, Path] = {
    "assignment.md": RAW_ASSIGNMENTS,
    "rubric.md": RAW_RUBRICS,
    "expected-solution.md": RAW_EXPECTED,
    "policies.md": RAW_POLICIES,
    "sample-feedback.md": RAW_FEEDBACK,
}

_STUB_HEADERS: dict[str, str] = {
    "assignment.md": "# Assignment\n\n<!-- Paste or write the assignment prompt here. -->\n",
    "rubric.md": "# Rubric\n\n<!-- Paste or write the grading rubric here. -->\n",
    "expected-solution.md": "# Expected Solution\n\n<!-- Describe the ideal solution or key criteria. -->\n",
    "common-mistakes.md": "# Common Mistakes\n\n<!-- Document typical student errors for this assignment. -->\n",
    "policies.md": "# Policies\n\n<!-- Summarize relevant course policies (late work, academic integrity, etc.). -->\n",
    "sample-feedback.md": "# Sample Feedback\n\n<!-- Provide example feedback comments for common scenarios. -->\n",
}


def _find_raw_source(packet_file: str, course: str, assignment: str, base_dir: Path) -> Path | None:
    """Search for an existing raw source file matching the course/assignment.

    Looks for files named ``{assignment}.md`` or ``{assignment}.txt`` inside
    ``{raw_dir}/{course}/`` and then directly inside ``{raw_dir}/``.

    Args:
        packet_file: The target packet filename (e.g. ``"assignment.md"``).
        course: The course identifier.
        assignment: The assignment identifier.
        base_dir: Repository root used to resolve raw source paths.

    Returns:
        A :class:`~pathlib.Path` to the found file, or ``None`` if not found.
    """
    raw_rel = _RAW_LOOKUP.get(packet_file)
    if raw_rel is None:
        return None

    raw_dir = base_dir / raw_rel
    stem = Path(packet_file).stem  # e.g. "assignment", "rubric"
    candidates = [
        raw_dir / course / f"{assignment}.md",
        raw_dir / course / f"{assignment}.txt",
        raw_dir / f"{course}-{assignment}.md",
        raw_dir / f"{course}-{assignment}.txt",
        raw_dir / course / f"{stem}.md",
        raw_dir / course / f"{stem}.txt",
    ]
    for candidate in candidates:
        if candidate.is_file():
            logging.debug("Found raw source for %s: %s", packet_file, candidate)
            return candidate
    return None


def create_grading_packet(course: str, assignment: str, base_dir: Path = Path(".")) -> Path:
    """Create a grading packet directory for *course* / *assignment*.

    For each expected packet file the function first attempts to copy a
    matching file from the appropriate ``raw/`` subdirectory.  If no source
    file is found it writes a stub with instructional placeholder text.

    Args:
        course: Short course identifier, e.g. ``"databases"``.
        assignment: Assignment identifier, e.g. ``"assignment-01"``.
        base_dir: Repository root directory (defaults to current directory).

    Returns:
        The :class:`~pathlib.Path` of the created packet directory.

    Raises:
        FileExistsError: If the packet directory already exists.
    """
    packet_dir = base_dir / PACKET_ROOT / f"{course}-{assignment}"

    if packet_dir.exists():
        raise FileExistsError(
            f"Packet directory already exists: {packet_dir}. "
            "Remove it first or choose a different course/assignment name."
        )

    packet_dir.mkdir(parents=True)
    logging.info("Created packet directory: %s", packet_dir)

    for filename in PACKET_FILES:
        dest = packet_dir / filename
        raw_source = _find_raw_source(filename, course, assignment, base_dir)
        if raw_source is not None:
            shutil.copy2(raw_source, dest)
            logging.info("Copied %s → %s", raw_source, dest)
        else:
            stub_text = _STUB_HEADERS.get(filename, f"# {filename}\n\n<!-- Add content here. -->\n")
            dest.write_text(stub_text, encoding="utf-8")
            logging.info("Created stub: %s", dest)

    return packet_dir


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a grading packet folder for a new assignment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python scripts/create_grading_packet.py \\\n"
            "    --course databases --assignment assignment-01\n"
            "\n"
            "Output:\n"
            "  processed/grading-packets/databases-assignment-01/\n"
        ),
    )
    parser.add_argument("--course", required=True, help="Short course identifier, e.g. 'databases'")
    parser.add_argument("--assignment", required=True, help="Assignment identifier, e.g. 'assignment-01'")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Repository root directory (default: current directory)",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level (e.g. INFO, DEBUG)")
    return parser.parse_args()


def main() -> None:
    """Entry point for the grading packet generator CLI."""
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s: %(message)s",
    )

    try:
        packet_dir = create_grading_packet(
            course=args.course,
            assignment=args.assignment,
            base_dir=Path(args.base_dir),
        )
        logging.info("Grading packet created at: %s", packet_dir)
    except FileExistsError as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from exc
    except OSError as exc:
        logging.error("Failed to create grading packet: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
