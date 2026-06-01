"""Remove student-identifiable information from text files.

Detects and replaces the following patterns with safe placeholders:

- Email addresses → ``[EMAIL_REDACTED]``
- Student ID numbers → ``[STUDENT_ID_REDACTED]``
- GitHub usernames when explicitly labeled → ``[GITHUB_REDACTED]``
- Names following labels such as ``Name:``, ``Student:``, ``Submitted By:`` → ``[NAME_REDACTED]``
- File path segments that appear to contain student names → ``[PATH_REDACTED]``

Usage::

    python scripts/anonymize_submissions.py \\
        --input-dir raw/sample-submissions \\
        --output-dir processed/anonymized

The folder structure under ``--input-dir`` is preserved under ``--output-dir``.
Only ``.txt`` and ``.md`` files are processed; all other files are copied
unchanged.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Redaction patterns
# ---------------------------------------------------------------------------

# RFC-5321-style email address.
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

# Student / university ID: 6–10 consecutive digits that are not part of a
# longer number (e.g. a year like 2024 is excluded by the word-boundary).
_STUDENT_ID_RE = re.compile(r"\b\d{6,10}\b")

# GitHub username when preceded by an explicit label on the same line.
_GITHUB_RE = re.compile(
    r"(?i)(github(?:\s+username)?|gh)\s*[:\-]\s*@?([A-Za-z0-9](?:[A-Za-z0-9\-]{0,37}[A-Za-z0-9])?)",
)

# Name following a common label.  Captures the rest of the line after the
# colon so that multi-word names are fully removed.
_NAME_LABEL_RE = re.compile(
    r"(?im)^(Name|Student|Submitted\s+By)\s*:\s*(.+)$",
)

# File path segment that looks like a personal name directory, e.g.
# "/home/john_doe/" or "submissions/Jane Smith/".
_PATH_NAME_RE = re.compile(
    r"(?:^|(?<=[/\\]))([A-Z][a-z]+[_\s][A-Z][a-z]+)(?=[/\\]|$)",
)

TEXT_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md"})


# ---------------------------------------------------------------------------
# Core redaction logic
# ---------------------------------------------------------------------------


def redact_emails(text: str) -> str:
    """Replace email addresses with ``[EMAIL_REDACTED]``."""
    return _EMAIL_RE.sub("[EMAIL_REDACTED]", text)


def redact_student_ids(text: str) -> str:
    """Replace standalone 6–10 digit numbers with ``[STUDENT_ID_REDACTED]``."""
    return _STUDENT_ID_RE.sub("[STUDENT_ID_REDACTED]", text)


def redact_github_usernames(text: str) -> str:
    """Replace explicitly labeled GitHub usernames with ``[GITHUB_REDACTED]``."""

    def _replace(match: re.Match[str]) -> str:
        label = match.group(1)
        return f"{label}: [GITHUB_REDACTED]"

    return _GITHUB_RE.sub(_replace, text)


def redact_name_labels(text: str) -> str:
    """Replace names following common student-identifying labels with ``[NAME_REDACTED]``."""

    def _replace(match: re.Match[str]) -> str:
        label = match.group(1)
        return f"{label}: [NAME_REDACTED]"

    return _NAME_LABEL_RE.sub(_replace, text)


def redact_path_names(text: str) -> str:
    """Replace path segments that look like personal-name directories with ``[PATH_REDACTED]``."""
    return _PATH_NAME_RE.sub("[PATH_REDACTED]", text)


def anonymize_text(text: str) -> str:
    """Apply all redaction passes to *text* and return the anonymized result.

    The order of passes matters: emails are removed first so that the local
    part of an address is not accidentally matched by later patterns.

    Args:
        text: Raw text that may contain student-identifiable information.

    Returns:
        Anonymized text with placeholders substituted for PII.
    """
    text = redact_emails(text)
    text = redact_github_usernames(text)
    text = redact_name_labels(text)
    text = redact_path_names(text)
    text = redact_student_ids(text)
    return text


# ---------------------------------------------------------------------------
# File / directory helpers
# ---------------------------------------------------------------------------


def anonymize_file(input_path: Path, output_path: Path) -> None:
    """Anonymize a single text file and write the result to *output_path*.

    Non-text files are copied unchanged.

    Args:
        input_path: Source file to anonymize.
        output_path: Destination path for the anonymized copy.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if input_path.suffix.lower() in TEXT_EXTENSIONS:
        raw_text = input_path.read_text(encoding="utf-8", errors="replace")
        cleaned = anonymize_text(raw_text)
        output_path.write_text(cleaned, encoding="utf-8")
        logging.debug("Anonymized: %s → %s", input_path, output_path)
    else:
        shutil.copy2(input_path, output_path)
        logging.debug("Copied (non-text): %s → %s", input_path, output_path)


def anonymize_directory(input_dir: Path, output_dir: Path) -> tuple[int, int]:
    """Recursively anonymize all files in *input_dir* into *output_dir*.

    Preserves the folder structure from *input_dir* under *output_dir*.

    Args:
        input_dir: Root directory containing submissions to anonymize.
        output_dir: Root directory for anonymized output.

    Returns:
        A tuple ``(anonymized_count, copied_count)`` where *anonymized_count*
        is the number of text files redacted and *copied_count* is the number
        of non-text files copied unchanged.

    Raises:
        FileNotFoundError: If *input_dir* does not exist.
    """
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    anonymized = 0
    copied = 0

    for src in sorted(input_dir.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(input_dir)
        dest = output_dir / rel
        anonymize_file(src, dest)
        if src.suffix.lower() in TEXT_EXTENSIONS:
            anonymized += 1
        else:
            copied += 1

    return anonymized, copied


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Anonymize student submissions by removing identifiable information.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python scripts/anonymize_submissions.py \\\n"
            "      --input-dir raw/sample-submissions \\\n"
            "      --output-dir processed/anonymized\n"
        ),
    )
    parser.add_argument(
        "--input-dir",
        default="raw/sample-submissions",
        help="Directory containing raw submissions (default: raw/sample-submissions)",
    )
    parser.add_argument(
        "--output-dir",
        default="processed/anonymized",
        help="Directory for anonymized output (default: processed/anonymized)",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level (e.g. INFO, DEBUG)")
    return parser.parse_args()


def main() -> None:
    """Entry point for the submission anonymizer CLI."""
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s: %(message)s",
    )

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    try:
        anonymized, copied = anonymize_directory(input_dir, output_dir)
        logging.info(
            "Anonymization complete. Text files redacted=%s, Other files copied=%s",
            anonymized,
            copied,
        )
    except FileNotFoundError as exc:
        logging.error("%s", exc)
        raise SystemExit(1) from exc
    except OSError as exc:
        logging.error("Anonymization failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
