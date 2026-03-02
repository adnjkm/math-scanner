#!/usr/bin/env python3
"""scanner.py — PDF/PNG → LaTeX Worksheet Generator CLI."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

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


def _render_mmd(mmd_content: str, output_path: str) -> None:
    """Render Mathpix Markdown to PDF via pandoc."""
    import shutil
    if not shutil.which("pandoc"):
        raise RuntimeError("pandoc not found. Install with: brew install pandoc")

    from src.compiler import find_pdflatex
    pdflatex = find_pdflatex()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write(mmd_content)
        tmp_mmd = f.name

    try:
        result = subprocess.run(
            [
                "pandoc", tmp_mmd,
                "-f", "markdown+tex_math_single_backslash",
                "-o", output_path,
                f"--pdf-engine={pdflatex}",
            ],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed:\n{result.stderr.strip()}")
    finally:
        os.unlink(tmp_mmd)


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
        "--backend",
        choices=["claude", "nougat"],
        default="claude",
        help="OCR backend to use (default: claude)",
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

        if args.backend == "nougat":
            from src.nougat_extractor import extract_raw_mmd, format_mmd

            page_mmds = []
            for i, img_path in enumerate(image_paths, start=1):
                print(f"Processing page {i}/{len(image_paths)}: running nougat...")
                raw_mmd = extract_raw_mmd(img_path)
                page_mmds.append(format_mmd(raw_mmd))

            combined_mmd = "\n\n".join(page_mmds)
            print(f"Rendering .mmd → {args.output}")
            _render_mmd(combined_mmd, args.output)
        else:
            from src.claude_extractor import extract_page_latex

            page_bodies = []
            for i, img_path in enumerate(image_paths, start=1):
                print(f"Processing page {i}/{len(image_paths)} with claude...")
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
