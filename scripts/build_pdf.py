"""Compile a .tex file to PDF next to it, using the classes in templates/.

Usage: python scripts/build_pdf.py applications/2026-10-foo/cv.tex [more.tex ...]
Auxiliary files go to a .build/ folder beside the .tex so the folder stays clean.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIKTEX_BIN = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/MiKTeX/miktex/bin/x64"


def latexmk():
    found = shutil.which("latexmk") or (MIKTEX_BIN / "latexmk.exe")
    return str(found)


def build(tex):
    tex = Path(tex).resolve()
    env = dict(os.environ)
    env["TEXINPUTS"] = f"{ROOT / 'templates'}{os.pathsep}" + env.get("TEXINPUTS", "")
    env["PATH"] = f"{MIKTEX_BIN}{os.pathsep}C:/Strawberry/perl/bin{os.pathsep}" + env["PATH"]
    cmd = [latexmk(), "-pdf", "-interaction=nonstopmode", "-halt-on-error",
           "-auxdir=.build", "-outdir=.", tex.name]
    result = subprocess.run(cmd, cwd=tex.parent, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    pdf = tex.with_suffix(".pdf")
    if result.returncode != 0 or not pdf.exists():
        log = tex.parent / ".build" / tex.with_suffix(".log").name
        tail = log.read_text(encoding="utf-8", errors="replace")[-3000:] if log.exists() else result.stdout[-3000:]
        print(f"FAILED: {tex}\n{tail}")
        return False
    pages = count_pages(pdf)
    print(f"OK: {pdf} ({pages} page{'s' if pages != 1 else ''})")
    return True


def count_pages(pdf):
    try:
        import pypdf
        return len(pypdf.PdfReader(pdf).pages)
    except Exception:
        return "?"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ok = all([build(t) for t in sys.argv[1:]])
    sys.exit(0 if ok else 1)
