"""src/nougat_extractor.py — Nougat OCR + Claude formatting for a single page image."""

import os
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


FORMAT_PROMPT = """You are formatting a math worksheet. Below is raw OCR output in Mathpix Markdown.

Rules:
- Add a blank line between each numbered question (1. 2. 3. etc.)
- Put each sub-question (a) b) c) etc.) on its own line
- Do not change any math, text, or LaTeX content whatsoever
- Return ONLY the reformatted Markdown, no explanation

{mmd_content}"""


def format_mmd(raw_mmd: str, model: str = None) -> str:
    """Use Claude to add line breaks and structure to raw nougat .mmd text."""
    if not shutil.which("claude"):
        raise RuntimeError("claude CLI not found in PATH.")

    prompt = FORMAT_PROMPT.format(mmd_content=raw_mmd)
    cmd = ["claude", "-p", prompt]
    if model:
        cmd += ["--model", model]

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        raise RuntimeError("claude CLI timed out while formatting .mmd")
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


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
    """Run nougat on an image and return the raw .mmd string.

    Caches the result as <image_stem>.mmd next to the image — if that file
    already exists, nougat is skipped entirely.
    """
    image_path = Path(image_path)
    cache_path = image_path.with_suffix(".mmd")

    if cache_path.exists():
        print(f"  Using cached nougat output: {cache_path.name}")
        return cache_path.read_text(encoding="utf-8").strip()

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        raise RuntimeError("Pillow is required for image-to-PDF conversion.")

    with tempfile.TemporaryDirectory(prefix="nougat_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        tmp_pdf = tmp_dir_path / "page.pdf"
        _image_to_pdf(str(image_path), tmp_pdf)
        raw_mmd = _run_nougat(tmp_pdf, tmp_dir_path)

    cache_path.write_text(raw_mmd, encoding="utf-8")
    print(f"  Saved nougat output to: {cache_path.name}")
    return raw_mmd


