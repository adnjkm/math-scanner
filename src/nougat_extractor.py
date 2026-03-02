"""src/nougat_extractor.py — Nougat OCR + Claude formatting for a single page image."""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _nougat_bin() -> str:
    """Return the nougat executable path, checking the current venv before PATH."""
    venv_nougat = Path(sys.executable).parent / "nougat"
    if venv_nougat.exists():
        return str(venv_nougat)
    on_path = shutil.which("nougat")
    if on_path:
        return on_path
    raise RuntimeError(
        "nougat not found. Install it with: pip install nougat-ocr"
    )


def format_mmd(raw_mmd: str) -> str:
    """Add spacing and indentation to raw nougat .mmd output using simple string logic."""
    # Put each numbered question (1. 2. 3. ...) on its own line with a blank line before it
    text = re.sub(r'(?<!\n)(\d+\. )', r'\n\n\1', raw_mmd)

    # Put each sub-question on its own indented line.
    # Nougat outputs them as: " a) ...", " b) ...", or " **a**) ...", " **b**) ..."
    text = re.sub(r' (\*\*[a-z]\*\*\))', r'\n    \1', text)  # bold variant
    text = re.sub(r' ([a-z]\))', r'\n    \1', text)           # plain variant

    return text.strip()


def _image_to_pdf(image_path: str, pdf_path: Path) -> None:
    """Embed an image on a padded letter-size page and save as PDF."""
    from PIL import Image
    dpi = 300
    img = Image.open(image_path).convert("RGB")
    letter_w, letter_h = int(8.5 * dpi), int(11 * dpi)
    if img.width > img.height:
        letter_w, letter_h = letter_h, letter_w
    margin = 200
    img.thumbnail((letter_w - margin * 2, letter_h - margin * 2), Image.LANCZOS)
    page = Image.new("RGB", (letter_w, letter_h), (255, 255, 255))
    page.paste(img, ((letter_w - img.width) // 2, (letter_h - img.height) // 2))
    page.save(str(pdf_path), "PDF", resolution=dpi)


def _run_nougat(pdf_path: Path, out_dir: Path) -> str:
    """Run nougat on a PDF and return the .mmd content."""
    nougat = _nougat_bin()
    cmd = [nougat, str(pdf_path), "-o", str(out_dir), "--no-skipping"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"nougat failed:\n{result.stderr.strip()}")
    mmd_path = out_dir / (pdf_path.stem + ".mmd")
    if not mmd_path.exists() or mmd_path.stat().st_size == 0:
        raise RuntimeError(f"nougat produced no output for {pdf_path.name}")
    return mmd_path.read_text(encoding="utf-8").strip()


def extract_raw_mmd(image_path: str) -> str:
    """Step 1: run nougat on an image and return the raw .mmd string."""
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        raise RuntimeError("Pillow is required for image-to-PDF conversion.")

    with tempfile.TemporaryDirectory(prefix="nougat_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        tmp_pdf = tmp_dir_path / "page.pdf"
        _image_to_pdf(image_path, tmp_pdf)
        return _run_nougat(tmp_pdf, tmp_dir_path)


