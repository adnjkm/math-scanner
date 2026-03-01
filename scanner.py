#!/usr/bin/env python3
"""scanner.py — PDF/PNG → LaTeX Worksheet Generator CLI."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from src.claude_extractor import extract_page_latex
from src.latex_gen import wrap_latex_document
from src.compiler import compile_latex


def pdf_to_images(pdf_path: str, dpi: int) -> list[str]:
    """Convert a PDF to a list of temporary PNG file paths."""
    from pdf2image import convert_from_path

    pages = convert_from_path(pdf_path, dpi=dpi)
    tmp_dir = tempfile.mkdtemp(prefix="math_scanner_")
    paths = []
    for i, page in enumerate(pages):
        img_path = os.path.join(tmp_dir, f"page_{i + 1:03d}.png")
        page.save(img_path, "PNG")
        paths.append(img_path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract math questions from a PDF or image and generate a LaTeX worksheet."
    )
    parser.add_argument("input", help="Path to input PDF or image (PNG/JPG)")
    parser.add_argument(
        "--output",
        default="output/worksheet.pdf",
        help="Output PDF path (default: output/worksheet.pdf)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PDF-to-image conversion (default: 300)",
    )
    parser.add_argument(
        "--claude-model",
        default=None,
        help="Claude model to use (default: Claude's own default)",
    )
    parser.add_argument(
        "--title",
        default="Calculus Worksheet",
        help="Worksheet title in the header (default: Calculus Worksheet)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    suffix = input_path.suffix.lower()
    image_paths = []
    tmp_dir_to_clean = None

    try:
        if suffix == ".pdf":
            print(f"Converting PDF to images at {args.dpi} DPI...")
            image_paths = pdf_to_images(str(input_path), args.dpi)
            tmp_dir_to_clean = str(Path(image_paths[0]).parent)
            print(f"  {len(image_paths)} page(s) extracted.")
        elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            image_paths = [str(input_path)]
        else:
            print(f"Error: unsupported file type '{suffix}'", file=sys.stderr)
            sys.exit(1)

        page_bodies = []
        for i, img_path in enumerate(image_paths, start=1):
            print(f"Processing page {i}/{len(image_paths)} with Claude...")
            page_bodies.append(extract_page_latex(img_path, model=args.claude_model))

        latex_source = wrap_latex_document("\n\n".join(page_bodies), title=args.title)

        print(f"Compiling PDF → {args.output}")
        compile_latex(latex_source, args.output)
        print(f"Done. Worksheet saved to: {args.output}")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: pdflatex timed out.", file=sys.stderr)
        sys.exit(1)
    finally:
        if tmp_dir_to_clean and Path(tmp_dir_to_clean).exists():
            import shutil
            shutil.rmtree(tmp_dir_to_clean, ignore_errors=True)


if __name__ == "__main__":
    main()
