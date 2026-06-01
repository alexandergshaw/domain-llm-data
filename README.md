# domain-llm-data

A lightweight data-preparation repository for building domain-specific LLM training data. Use it to collect raw documents, clean them into plain text, and draft instruction-tuning examples in JSONL format.

## Folder structure

```text
raw/
  syllabi/
  assignments/
  rubrics/
  resumes/
  cover-letters/
  code-examples/
cleaned/
examples/
scripts/
tests/
README.md
requirements.txt
.gitignore
```

## Add source documents

Place source documents recursively under `raw/` using the category folders above.

Supported formats for cleaning:
- `.txt`
- `.md`
- `.docx`
- `.pdf`

## Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the text cleaner

```bash
python scripts/clean_text.py --raw-dir raw --cleaned-dir cleaned
```

What it does:
- recursively reads files from `raw/`
- extracts readable text from supported formats
- normalizes whitespace and removes repeated blank lines
- writes `.txt` files into `cleaned/` while preserving folder structure
- logs skipped unsupported files

### Expected cleaner output

For `raw/syllabi/week1/intro.md`, output is written to:

```text
cleaned/syllabi/week1/intro.txt
```

## Create draft instruction examples

```bash
python scripts/create_examples.py --cleaned-dir cleaned --output-file examples/instruction_examples.jsonl
```

Use `--overwrite` to replace an existing output file:

```bash
python scripts/create_examples.py --overwrite
```

The script:
- reads cleaned `.txt` files
- splits content into chunks
- infers a category (`course_design`, `assignment`, `rubric`, `resume`, `cover_letter`, `code_explanation`, `professional_email`)
- writes JSONL draft records with fields: `instruction`, `input`, `output`, `source_file`, `category`

## Example JSONL format

```json
{"instruction":"Explain the assignment requirements and expected deliverables in clear, student-friendly language.","input":"...chunked text...","output":"","source_file":"assignments/week2.txt","category":"assignment"}
```
