"""Validate grading examples stored in a JSONL file.

Each line must be valid JSON containing the following top-level fields:

- ``instruction`` (str)
- ``input`` (dict) with keys: ``course``, ``assignment_id``, ``assignment_prompt``,
  ``rubric``, ``student_submission``
- ``output`` (dict) with keys: ``score``, ``points_possible``, ``rubric_breakdown``,
  ``summary_feedback``, ``revision_priorities``, ``flags``
- ``category`` (str)

Additional constraints:

- ``output.score`` must be numeric (int or float).
- ``output.points_possible`` must be numeric (int or float).
- ``output.rubric_breakdown`` must be a list.

Usage::

    python scripts/validate_grading_examples.py examples/grading_examples.jsonl

The script prints a summary of statistics and exits with a non-zero status
code if any validation errors are found.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL: tuple[str, ...] = ("instruction", "input", "output", "category")

REQUIRED_INPUT_FIELDS: tuple[str, ...] = (
    "course",
    "assignment_id",
    "assignment_prompt",
    "rubric",
    "student_submission",
)

REQUIRED_OUTPUT_FIELDS: tuple[str, ...] = (
    "score",
    "points_possible",
    "rubric_breakdown",
    "summary_feedback",
    "revision_priorities",
    "flags",
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_record(record: dict[str, Any], line_number: int) -> list[str]:
    """Validate a single parsed grading-example record.

    Args:
        record: Parsed dictionary from one JSONL line.
        line_number: 1-based line number used in error messages.

    Returns:
        A (possibly empty) list of human-readable error strings.
    """
    errors: list[str] = []
    prefix = f"Line {line_number}"

    # --- top-level required fields ---
    for field in REQUIRED_TOP_LEVEL:
        if field not in record:
            errors.append(f"{prefix}: missing top-level field '{field}'")

    # --- input sub-fields ---
    input_val = record.get("input")
    if isinstance(input_val, dict):
        for field in REQUIRED_INPUT_FIELDS:
            if field not in input_val:
                errors.append(f"{prefix}: missing input field '{field}'")
    elif input_val is not None:
        errors.append(f"{prefix}: 'input' must be a JSON object, got {type(input_val).__name__}")

    # --- output sub-fields and type checks ---
    output_val = record.get("output")
    if isinstance(output_val, dict):
        for field in REQUIRED_OUTPUT_FIELDS:
            if field not in output_val:
                errors.append(f"{prefix}: missing output field '{field}'")

        score = output_val.get("score")
        if score is not None and not isinstance(score, (int, float)):
            errors.append(
                f"{prefix}: 'output.score' must be numeric, got {type(score).__name__}"
            )

        points_possible = output_val.get("points_possible")
        if points_possible is not None and not isinstance(points_possible, (int, float)):
            errors.append(
                f"{prefix}: 'output.points_possible' must be numeric, "
                f"got {type(points_possible).__name__}"
            )

        rubric_breakdown = output_val.get("rubric_breakdown")
        if rubric_breakdown is not None and not isinstance(rubric_breakdown, list):
            errors.append(
                f"{prefix}: 'output.rubric_breakdown' must be a list, "
                f"got {type(rubric_breakdown).__name__}"
            )
    elif output_val is not None:
        errors.append(
            f"{prefix}: 'output' must be a JSON object, got {type(output_val).__name__}"
        )

    return errors


def validate_file(path: Path) -> tuple[int, int, list[str]]:
    """Validate all records in a JSONL file.

    Args:
        path: Path to the ``.jsonl`` file to validate.

    Returns:
        A tuple ``(total, valid, errors)`` where *total* is the number of
        lines processed, *valid* is the count of lines that passed all checks,
        and *errors* is a flat list of human-readable error strings.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    total = 0
    all_errors: list[str] = []
    invalid_lines: set[int] = set()

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue  # skip blank lines

            total += 1

            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                all_errors.append(f"Line {line_number}: invalid JSON — {exc}")
                invalid_lines.add(line_number)
                continue

            if not isinstance(record, dict):
                all_errors.append(
                    f"Line {line_number}: expected a JSON object, got {type(record).__name__}"
                )
                invalid_lines.add(line_number)
                continue

            record_errors = validate_record(record, line_number)
            if record_errors:
                invalid_lines.add(line_number)
                all_errors.extend(record_errors)

    valid = total - len(invalid_lines)
    return total, valid, all_errors


# ---------------------------------------------------------------------------
# Summary reporting
# ---------------------------------------------------------------------------


def print_summary(path: Path, total: int, valid: int, errors: list[str]) -> None:
    """Print validation statistics and any error messages to stdout.

    Args:
        path: The validated file path (used in the header).
        total: Total number of non-blank lines processed.
        valid: Number of lines that passed all validations.
        errors: List of error strings to display.
    """
    invalid = total - valid
    print(f"\n{'=' * 60}")
    print(f"Validation report: {path}")
    print(f"{'=' * 60}")
    print(f"  Total records : {total}")
    print(f"  Valid         : {valid}")
    print(f"  Invalid       : {invalid}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  • {err}")
    else:
        print("\n✓ All records passed validation.")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Validate a grading examples JSONL file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python scripts/validate_grading_examples.py examples/grading_examples.jsonl\n"
        ),
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="examples/grading_examples.jsonl",
        help="Path to the JSONL file to validate (default: examples/grading_examples.jsonl)",
    )
    parser.add_argument("--log-level", default="WARNING", help="Logging level (e.g. INFO, DEBUG)")
    return parser.parse_args()


def main() -> None:
    """Entry point for the grading example validator CLI."""
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.WARNING),
        format="%(levelname)s: %(message)s",
    )

    path = Path(args.file)

    try:
        total, valid, errors = validate_file(path)
    except FileNotFoundError as exc:
        logging.error("%s", exc)
        sys.exit(1)

    print_summary(path, total, valid, errors)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
