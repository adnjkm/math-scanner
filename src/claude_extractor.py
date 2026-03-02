"""src/claude_extractor.py — Claude vision + LaTeX extraction for a single page image."""

import os
import shutil
import subprocess

PAGE_PROMPT_TEMPLATE = """You are a LaTeX math typesetter creating a handwritten worksheet.

Read the image at: {image_path}

Extract ALL math problems visible on this page. Return ONLY LaTeX body content — no \\documentclass, no preamble, no \\begin{{document}}, no explanation.

Layout rules:
- Problems starting with a number (1., 2., 3. etc.) → typeset as:
    \\textbf{{1.}} <question in LaTeX math>
    \\vspace{{0.3cm}}

- Sub-problems starting with a letter (a., b., a), b) etc.) → typeset as:
    \\hspace{{1cm}}\\textbf{{(a)}} <sub-question in LaTeX math>\\\\[0.2cm]
    \\vspace{{Xcm}}

  where X = 4 (simple 1-step), 7 (multi-step), 12 (complex/multi-part)

Use proper LaTeX: $...$ inline, \\frac{{}}{{}}, \\int_{{}}^{{}}, \\lim, \\sqrt{{}}, etc.
Return ONLY the LaTeX body content."""


def extract_page_latex(image_path: str, model: str = None) -> str:
    """Call claude CLI to read an image and return formatted LaTeX body content."""
    if not shutil.which("claude"):
        raise RuntimeError(
            "claude CLI not found in PATH. Ensure Claude Code is installed."
        )

    prompt = PAGE_PROMPT_TEMPLATE.format(image_path=image_path)
    cmd = ["claude", "-p", prompt]
    if model:
        cmd += ["--model", model]

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed:\n{result.stderr.strip()}")

    raw = result.stdout.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()

    return raw
