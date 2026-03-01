import shutil
import subprocess
import tempfile
from pathlib import Path


def find_pdflatex() -> str:
    """Return path to pdflatex, or raise RuntimeError with install instructions."""
    path = shutil.which("pdflatex")
    if path:
        return path
    # macOS TeX Live installs outside PATH until terminal restart — check directly
    import glob
    candidates = glob.glob("/usr/local/texlive/*/bin/universal-darwin/pdflatex") + \
                 glob.glob("/usr/local/texlive/*/bin/aarch64-darwin/pdflatex") + \
                 glob.glob("/Library/TeX/texbin/pdflatex")
    if candidates:
        return sorted(candidates)[-1]  # pick most recent year
    raise RuntimeError(
        "pdflatex not found. Install it with:\n"
        "  brew install --cask basictex\n"
        "Then restart your terminal."
    )


def compile_latex(latex_source: str, output_path: str) -> None:
    """Compile a LaTeX string to a PDF at output_path."""
    pdflatex = find_pdflatex()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tex_file = Path(tmp_dir) / "worksheet.tex"
        tex_file.write_text(latex_source, encoding="utf-8")

        try:
            for _ in range(2):
                result = subprocess.run(
                    [pdflatex, "-interaction=nonstopmode", str(tex_file)],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    error_lines = [
                        line for line in result.stdout.splitlines()
                        if line.startswith("!")
                    ]
                    error_summary = "\n".join(error_lines) or result.stdout[-500:]
                    raise RuntimeError(
                        f"pdflatex failed (exit {result.returncode}):\n{error_summary}"
                    )
        finally:
            pass  # tempdir cleanup handled by context manager

        pdf_file = Path(tmp_dir) / "worksheet.pdf"
        if not pdf_file.exists():
            raise RuntimeError("pdflatex ran but produced no PDF.")

        shutil.copy2(str(pdf_file), str(output_path))
