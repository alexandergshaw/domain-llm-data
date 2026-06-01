"""Create draft instruction-tuning JSONL examples from cleaned text files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CATEGORY_FROM_PATH = {
    "syllabi": "course_design",
    "assignments": "assignment",
    "rubrics": "rubric",
    "resumes": "resume",
    "cover-letters": "cover_letter",
    "code-examples": "code_explanation",
}

INSTRUCTION_TEMPLATES = {
    "course_design": "Draft a concise course design summary and learning outcomes from the provided material.",
    "assignment": "Explain the assignment requirements and expected deliverables in clear, student-friendly language.",
    "rubric": "Summarize this rubric and describe how performance should be evaluated.",
    "resume": "Rewrite this resume section to improve clarity, impact, and professionalism.",
    "cover_letter": "Improve this cover letter text for clarity, tone, and relevance to the target role.",
    "code_explanation": "Explain the code example, including key concepts and practical takeaways.",
    "professional_email": "Draft a polished professional email based on the provided text.",
}


def infer_category(file_path: Path, cleaned_dir: Path) -> str:
    """Infer category from the file's first directory under cleaned_dir."""
    relative = file_path.relative_to(cleaned_dir)
    top_dir = relative.parts[0] if relative.parts else ""
    return CATEGORY_FROM_PATH.get(top_dir, "professional_email")


def split_into_chunks(text: str, max_chars: int = 1200) -> list[str]:
    """Split text into chunks close to max_chars, preferring paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(paragraph) <= max_chars:
                current = paragraph
            else:
                for start in range(0, len(paragraph), max_chars):
                    part = paragraph[start : start + max_chars].strip()
                    if part:
                        chunks.append(part)
                current = ""

    if current:
        chunks.append(current)

    return chunks


def build_records(file_path: Path, cleaned_dir: Path, max_chars: int) -> list[dict[str, str]]:
    """Build draft JSONL records from one cleaned file."""
    text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []

    category = infer_category(file_path, cleaned_dir)
    instruction = INSTRUCTION_TEMPLATES[category]
    chunks = split_into_chunks(text=text, max_chars=max_chars)

    records: list[dict[str, str]] = []
    relative_source = str(file_path.relative_to(cleaned_dir))
    for chunk in chunks:
        records.append(
            {
                "instruction": instruction,
                "input": chunk,
                "output": "",
                "source_file": relative_source,
                "category": category,
            }
        )

    return records


def create_examples(cleaned_dir: Path, output_file: Path, overwrite: bool, max_chars: int) -> int:
    """Create draft instruction examples from cleaned .txt files.

    Returns:
        Number of records written.
    """
    if output_file.exists() and not overwrite:
        raise FileExistsError(
            f"Output file exists: {output_file}. Pass --overwrite to replace it."
        )

    cleaned_files = sorted(path for path in cleaned_dir.rglob("*.txt") if path.is_file())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_file.open("w", encoding="utf-8") as handle:
        for file_path in cleaned_files:
            for record in build_records(file_path=file_path, cleaned_dir=cleaned_dir, max_chars=max_chars):
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    return count


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Create draft instruction-tuning examples from cleaned text files."
    )
    parser.add_argument("--cleaned-dir", default="cleaned", help="Directory containing cleaned .txt files")
    parser.add_argument(
        "--output-file",
        default="examples/instruction_examples.jsonl",
        help="Where to write draft JSONL examples",
    )
    parser.add_argument("--max-chars", type=int, default=1200, help="Maximum characters per input chunk")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    return parser.parse_args()


def main() -> None:
    """Run the example generation CLI."""
    args = parse_args()
    count = create_examples(
        cleaned_dir=Path(args.cleaned_dir),
        output_file=Path(args.output_file),
        overwrite=args.overwrite,
        max_chars=args.max_chars,
    )
    print(f"Wrote {count} draft examples to {args.output_file}")


if __name__ == "__main__":
    main()
