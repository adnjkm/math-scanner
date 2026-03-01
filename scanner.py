#!/usr/bin/env python3
"""scanner.py — PDF/PNG → LaTeX Worksheet Generator CLI."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from src.extractor import extract_questions_from_image
from src.latex_gen import generate_latex
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
    load_dotenv()

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
    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Validate API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key.",
            file=sys.stderr,
        )
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

        all_questions = []
        for i, img_path in enumerate(image_paths, start=1):
            print(f"Extracting questions from page {i}/{len(image_paths)}...")
            questions = extract_questions_from_image(img_path, api_key)
            all_questions.extend(questions)
            print(f"  Found {len(questions)} question(s).")

        if not all_questions:
            print("No questions found in the input. Exiting.", file=sys.stderr)
            sys.exit(1)

        # Renumber questions globally across pages
        for idx, q in enumerate(all_questions, start=1):
            q["number"] = str(idx)

        print(f"Total questions extracted: {len(all_questions)}")
        print("Generating LaTeX...")
        latex_source = generate_latex(all_questions)

        print(f"Compiling PDF → {args.output}")
        compile_latex(latex_source, args.output)
        print(f"Done. Worksheet saved to: {args.output}")

    except anthropic.APIError as e:
        print(f"Anthropic API error: {e}", file=sys.stderr)
        sys.exit(1)
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
