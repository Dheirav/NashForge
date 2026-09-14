"""
The phase-2 paper with Springer's llncs class, from the same content as the
Word version.

    venv/bin/python scripts/phase2/make_latex.py        # writes and compiles docs/latex/nashforge.tex

llncs.cls and splncs04.bst sit in docs/latex (fetched from CTAN). Figures are
referenced from docs/figures/phase2.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content import AUTHOR, EMAIL, INSTITUTE, TITLE, build  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIGS = os.path.join(ROOT, "docs", "figures", "phase2")
OUT_DIR = os.path.join(ROOT, "docs", "latex")
TEX = os.path.join(OUT_DIR, "nashforge.tex")


def esc(text):
    """Plain prose to LaTeX: the special characters, and the few symbols the text uses."""
    text = text.replace("\\", r"\textbackslash{}")
    for ch, rep in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                    ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        text = text.replace(ch, rep)
    text = text.replace("±", r"$\pm$").replace("−", r"$-$").replace("×", r"$\times$")
    text = text.replace("|", r"\textbar{}").replace("→", r"$\rightarrow$")
    text = re.sub(r'"([^"]*)"', r"``\1''", text)
    return text


def main():
    blocks = build()
    out = [r"\documentclass[runningheads]{llncs}",
           r"\usepackage[T1]{fontenc}", r"\usepackage[utf8]{inputenc}", r"\usepackage{graphicx}",
           r"\usepackage{booktabs}", r"\usepackage{array}", r"\usepackage{url}",
           r"\graphicspath{{../figures/phase2/}}",
           r"\begin{document}",
           r"\title{" + esc(TITLE) + "}",
           r"\titlerunning{NashForge: one instrument for three learning families}",
           r"\author{" + esc(AUTHOR) + "}",
           r"\authorrunning{D. Prakash}",
           r"\institute{" + esc(INSTITUTE) + r" \\ \email{" + EMAIL + "}}",
           r"\maketitle"]
    fig = tab = 0
    for block in blocks:
        kind = block[0]
        if kind == "abstract":
            out += [r"\begin{abstract}", esc(block[1]), r"\end{abstract}"]
        elif kind == "keywords":
            out.append(r"\keywords{" + esc(block[1]).replace(", ", r" \and ") + "}")
        elif kind == "h1":
            title = re.sub(r"^\d+\s+", "", block[1])
            if title == "References":
                continue
            out.append(r"\section{" + esc(title) + "}")
        elif kind == "h2":
            out.append(r"\subsection{" + esc(re.sub(r"^\d+\.\d+\s+", "", block[1])) + "}")
        elif kind == "p":
            out += [esc(block[1]), ""]
        elif kind == "figure":
            _, name, caption, width = block
            fig += 1
            out += [r"\begin{figure}[t]", r"\centering",
                    r"\includegraphics[width=%.1fcm]{%s}" % (min(width, 12.2), name),
                    r"\caption{" + esc(caption) + "}", r"\label{fig:%d}" % fig, r"\end{figure}", ""]
        elif kind == "table":
            _, caption, header, rows = block
            tab += 1
            spec = "l" + "r" * (len(header) - 1) if len(header) <= 5 else "l" * len(header)
            out += [r"\begin{table}[t]", r"\caption{" + esc(caption) + "}", r"\label{tab:%d}" % tab,
                    r"\centering", r"\small", r"\begin{tabular}{" + spec + "}", r"\toprule",
                    " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
            for row in rows:
                out.append(" & ".join(esc(str(v)) for v in row) + r" \\")
            out += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
        elif kind == "refs":
            out.append(r"\begin{thebibliography}{99}")
            for i, r in enumerate(block[1], 1):
                out.append(r"\bibitem{ref%d} " % i + esc(r))
            out.append(r"\end{thebibliography}")
    out.append(r"\end{document}")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(TEX, "w") as handle:
        handle.write("\n".join(out) + "\n")
    print("wrote", os.path.relpath(TEX, ROOT))
    if shutil.which("pdflatex"):
        for _ in range(2):
            done = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "nashforge.tex"],
                                  cwd=OUT_DIR, capture_output=True, text=True)
        if done.returncode == 0:
            print("compiled docs/latex/nashforge.pdf")
        else:
            tail = done.stdout[-1500:]
            print("pdflatex failed:\n" + tail)
            sys.exit(1)


if __name__ == "__main__":
    main()
