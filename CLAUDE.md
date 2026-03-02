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

Output is written to `output/worksheet.pdf` by default (gitignored).

---

## Nougat Backend (`--backend nougat`)

### What it does
Nougat (Meta's neural OCR) replaces Claude's vision step for reading the image.
Pipeline: image → padded letter-size PDF → nougat OCR → `.mmd` → Claude formats → pandoc → PDF.

### Additional system dependencies
```bash
brew install pandoc       # renders .mmd → PDF
# Python must be 3.11 — nougat is incompatible with 3.12+ and segfaults on 3.14
```

### Python version requirement: MUST be 3.11
Nougat's C extensions (torch) segfault on Python 3.14. Always use Python 3.11:
```bash
brew install pyenv
pyenv install 3.11
/Users/<you>/.pyenv/versions/3.11.x/bin/python3 -m venv .venv
```

### Pinned transitive dependencies (already in requirements.txt)
These MUST stay pinned or nougat will break at import time:

| Package | Pin | Why |
|---|---|---|
| `transformers` | `>=4.25.1,<4.38.0` | 4.38 added `cache_position` kwarg that breaks nougat's BARTDecoder |
| `albumentations` | `>=1.0.0,<2.0.0` | 2.0 changed `ImageCompression` API (int → string) |
| `pypdfium2` | `>=4.0.0,<5.0.0` | 5.0 removed the `render()` method nougat uses |
| `timm` | `==0.5.4` | exact pin from nougat's own metadata — do not upgrade |

### Nougat output caching
Nougat is slow (~30–60s/page). Both intermediate outputs are cached next to the input image:
- `textbook4.mmd` — raw nougat OCR output (skip nougat on re-run)
- `textbook4_formatted.mmd` — Claude-formatted output (skip Claude on re-run)

Delete these files to force a re-run of the respective step.

### Known limitations
- Nougat produces **empty output** for sparse/wide-format images (e.g. cropped strips, multi-column grids with lots of whitespace). Falls back to `--backend claude` for those.
- Nougat hallucinates sub-question labels (outputs all as `a)` instead of `a) b) c)`). This is an OCR error in the model, not fixable without retraining.
- The `claude` CLI **cannot be called as a subprocess from inside an active Claude Code session** even with `CLAUDECODE` unset — it times out. Format step must be run outside Claude Code, or use a different formatting approach.

### Run with nougat backend
```bash
NO_ALBUMENTATIONS_UPDATE=1 .venv/bin/python3 scanner.py textbook4.png --backend nougat
```
The `NO_ALBUMENTATIONS_UPDATE=1` env var suppresses a harmless upgrade warning from albumentations.

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
