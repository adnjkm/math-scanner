# CLAUDE.md

## GitHub Repo

This project is: **adnjkm/math-scanner**
Remote: https://github.com/adnjkm/math-scanner.git

## What This Project Does

**math-scanner** is a CLI tool that takes a calculus textbook page (PDF or PNG) and generates a clean PDF worksheet with the extracted questions and blank space for handwritten solutions (for use on iPad).

**Pipeline:**
1. If PDF input: convert pages to PNGs via `pdf2image` (needs `poppler`)
2. Call the `claude` CLI with the image + a LaTeX formatting prompt
3. Wrap the returned LaTeX body in a full document
4. Compile to PDF with `pdflatex` (needs BasicTeX)

**Entry point:** `scanner.py`
**Key source files:**
- `src/claude_extractor.py` — calls `claude` CLI with the image, returns LaTeX body
- `src/latex_gen.py` — wraps body in full LaTeX document (`wrap_latex_document`)
- `src/compiler.py` — runs `pdflatex` twice, searches known TeX Live paths if not on PATH
- `src/extractor.py` — legacy Ollama-based extractor (not used by current pipeline)

---

## Setup on a New Machine

### 1. System dependencies
```bash
brew install poppler                  # for PDF → image conversion
brew install --cask basictex          # for pdflatex (~100MB, needs sudo)
eval "$(/usr/libexec/path_helper)"   # add pdflatex to PATH (or restart terminal)
```

### 2. Python virtual environment
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Claude Code
Must be installed and authenticated — the pipeline calls the `claude` CLI directly.
No separate Anthropic API key is needed.

### 4. Run
```bash
.venv/bin/python3 scanner.py textbook1.png
# or
.venv/bin/python3 scanner.py textbook.pdf --output my_worksheet.pdf
```

**If running from inside a Claude Code session**, unset the nested-session guard first:
```bash
unset CLAUDECODE && .venv/bin/python3 scanner.py textbook1.png
```

Output is written to `output/worksheet.pdf` by default (gitignored).

---

## Git Workflow

After completing any meaningful unit of work, commit and push to GitHub so progress is never lost:

```bash
git add <specific files>
git commit -m "short imperative summary of what changed"
git push
```

Commit message guidelines:
- Use imperative mood: "add feature" not "added" or "adds"
- Be specific: describe *what* changed and *why* if non-obvious
- One logical change per commit — don't bundle unrelated changes
