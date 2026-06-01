# domain-llm-data

A data-preparation repository for building a rubric-based grading assistant and domain-specific grading LLM.  The repository handles collecting, organizing, anonymizing, and validating grading data from college courses so that it can eventually be used to train and evaluate a grading model.

No machine-learning code lives here.  This is purely a data-pipeline repository.

---

## Folder structure

```text
raw/
  assignments/          # Assignment prompts and instructions
  rubrics/              # Grading rubrics
  policies/             # Course and assignment policies
  expected-solutions/   # Instructor expected-solution notes
  sample-submissions/   # Raw student submissions (before anonymization)
  instructor-feedback/  # Existing instructor feedback examples

processed/
  grading-packets/      # Generated grading packets (one folder per assignment)

examples/
  grading_examples.jsonl   # Training examples in JSONL format
  grading_eval_set.jsonl   # Evaluation examples in JSONL format

scripts/
  clean_text.py              # Clean raw documents into plain text
  create_examples.py         # Draft instruction-tuning JSONL examples
  create_grading_packet.py   # Generate a grading packet for a new assignment
  anonymize_submissions.py   # Remove PII from student submissions
  validate_grading_examples.py  # Validate grading_examples.jsonl

templates/
  grading_example_template.json  # Template for a grading training example
  feedback_template.md           # Reusable feedback template

tests/                  # Unit tests for all scripts

README.md
requirements.txt
.gitignore
```

---

## Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Workflow

### 1. Create an assignment grading packet

Generate a ready-to-fill grading packet for a new assignment.  The script
copies matching files from `raw/` if they exist, otherwise it creates
placeholder stubs.

```bash
python scripts/create_grading_packet.py \
  --course databases \
  --assignment assignment-01
```

Output: `processed/grading-packets/databases-assignment-01/` containing:

```text
assignment.md
rubric.md
expected-solution.md
common-mistakes.md
policies.md
sample-feedback.md
```

### 2. Store assignment materials and rubrics

Place source documents in the appropriate `raw/` subdirectory:

| Content | Directory |
|---------|-----------|
| Assignment prompts | `raw/assignments/{course}/` |
| Grading rubrics | `raw/rubrics/{course}/` |
| Course policies | `raw/policies/{course}/` |
| Expected-solution notes | `raw/expected-solutions/{course}/` |
| Sample instructor feedback | `raw/instructor-feedback/{course}/` |

Supported formats: `.txt`, `.md`, `.docx`, `.pdf`

### 3. Collect submissions

Place raw student submissions under `raw/sample-submissions/{course}/{assignment}/`.

### 4. Anonymize submissions

Strip personally identifiable information (email addresses, student IDs, names,
GitHub usernames, file-path name segments) from all submissions.  Folder
structure is preserved.

```bash
python scripts/anonymize_submissions.py \
  --input-dir raw/sample-submissions \
  --output-dir processed/anonymized
```

Replaced patterns:

| Pattern | Placeholder |
|---------|-------------|
| Email address | `[EMAIL_REDACTED]` |
| Student ID (6–10 digits) | `[STUDENT_ID_REDACTED]` |
| Labeled GitHub username | `[GITHUB_REDACTED]` |
| Name following `Name:` / `Student:` / `Submitted By:` | `[NAME_REDACTED]` |
| Path segment matching `FirstName_LastName` | `[PATH_REDACTED]` |

### 5. Clean raw documents into plain text

```bash
python scripts/clean_text.py --raw-dir raw --cleaned-dir cleaned
```

### 6. Record grades and feedback

Fill in the generated grading packet files and use
`templates/grading_example_template.json` as a starting point when recording
a graded example.  Use `templates/feedback_template.md` for writing student
feedback.

Append completed examples to `examples/grading_examples.jsonl` (one JSON
object per line, following the template schema).

### 7. Validate examples

```bash
python scripts/validate_grading_examples.py examples/grading_examples.jsonl
```

Checks:
- All required top-level fields present (`instruction`, `input`, `output`, `category`)
- All required `input` sub-fields present
- All required `output` sub-fields present
- `score` and `points_possible` are numeric
- `rubric_breakdown` is a list
- Every line is valid JSON

Exits with a non-zero status code if any errors are found.

### 8. Build training dataset (general instruction tuning)

`create_examples.py` is a legacy script that generates generic instruction-tuning
examples from any cleaned text.  It is compatible with the new structure but
produces draft examples only — manual review and completion via
`grading_example_template.json` is required before adding records to
`grading_examples.jsonl`.

```bash
python scripts/create_examples.py \
  --cleaned-dir cleaned \
  --output-file examples/instruction_examples.jsonl
```

---

## Example JSONL format

```json
{
  "instruction": "Grade this assignment using the provided rubric.",
  "input": {
    "course": "databases",
    "assignment_id": "assignment-01",
    "assignment_prompt": "Design a normalized schema for a library system.",
    "rubric": "Correctness: 50 pts\nNormalization: 30 pts\nDocumentation: 20 pts",
    "expected_solution_notes": "3NF minimum; entities: Book, Author, Member, Loan.",
    "student_submission": "CREATE TABLE books (id INT PRIMARY KEY, title TEXT);",
    "test_results": "",
    "policy_notes": "Late submissions receive a 10% penalty per day."
  },
  "output": {
    "score": 62,
    "points_possible": 100,
    "rubric_breakdown": [
      {"criterion": "Correctness", "points_awarded": 32, "points_possible": 50, "feedback": "Missing Author and Loan tables."},
      {"criterion": "Normalization", "points_awarded": 20, "points_possible": 30, "feedback": "Books table is 1NF only."},
      {"criterion": "Documentation", "points_awarded": 10, "points_possible": 20, "feedback": "No comments or ER diagram."}
    ],
    "summary_feedback": "Good start but several required entities are missing.",
    "revision_priorities": ["Add Author, Member, and Loan tables", "Normalize to 3NF", "Add inline comments"],
    "flags": []
  },
  "category": "grading"
}
```

---

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

