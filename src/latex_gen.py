import re


_SPECIAL_CHARS = re.compile(r'([&%$#_{}~^\\])')

_LATEX_ESCAPE_MAP = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def escape_latex_special_chars(text: str) -> str:
    """Escape LaTeX special characters in plain text fields."""
    return _SPECIAL_CHARS.sub(lambda m: _LATEX_ESCAPE_MAP[m.group(0)], text)


def format_question_block(q: dict) -> str:
    """Format a single question dict into a LaTeX block."""
    number = escape_latex_special_chars(q["number"])
    latex_body = q["latex"]  # not escaped — already LaTeX
    space_cm = q["space_cm"]

    return (
        f"\\textbf{{{number}.}} {latex_body}\n\n"
        f"\\vspace{{{space_cm}cm}}\n"
        f"\\noindent\\rule{{\\textwidth}}{{0.4pt}}\n"
        f"\\vspace{{0.5cm}}\n"
    )


def wrap_latex_document(body: str, title: str = "Calculus Worksheet") -> str:
    """Wrap pre-formatted LaTeX body content in a complete compilable document."""
    return (
        f"\\documentclass[12pt]{{article}}\n"
        f"\\usepackage{{amsmath,amssymb,mathtools}}\n"
        f"\\usepackage[margin=2cm]{{geometry}}\n"
        f"\\pagestyle{{empty}}\n\n"
        f"\\begin{{document}}\n\n"
        f"{body}\n\n"
        f"\\end{{document}}\n"
    )


def generate_latex(questions: list[dict]) -> str:
    """Build a complete LaTeX document string from a list of question dicts."""
    preamble = r"""\documentclass[12pt]{article}
\usepackage[margin=2cm]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{mathtools}
\usepackage{fancyhdr}

\pagestyle{fancy}
\fancyhf{}
\lhead{Calculus Worksheet}
\rhead{Name: \underline{\hspace{5cm}}}
\cfoot{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\begin{document}
"""

    body_parts = [format_question_block(q) for q in questions]
    body = "\n".join(body_parts)

    footer = r"\end{document}"

    return preamble + body + "\n" + footer
