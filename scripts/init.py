"""Set up your personal workspace: create every gitignored file and folder from scaffold/.

Usage:
    python scripts/init.py                       # asks for your name and contact details
    python scripts/init.py --name "Jane Doe" --email jane@example.com --phone "+47 123 45 678" \
        --city "Oslo, Norway" --linkedin https://www.linkedin.com/in/jane-doe
    python scripts/init.py --yes                 # no questions; placeholders you can edit later

Existing files are never overwritten, so it is safe to run again (e.g. after pulling a new
version of the framework that adds scaffold files).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = ROOT / "scaffold"
EMPTY_DIRS = ["profile/experiences", "applications", "companies", "generated",
              "inbox/processed", "archive", "personal"]
TEXT_SUFFIXES = {".md", ".tex", ".txt"}

FIELDS = [  # (placeholder, prompt, default)
    ("NAME", "Full name as it should appear on your CV", "Your Name"),
    ("CITY", "City, Country", "City, Country"),
    ("EMAIL", "Email", "you@example.com"),
    ("PHONE", "Phone (with country code)", "+00 000 00 000"),
    ("LINKEDIN_URL", "LinkedIn URL (optional)", "https://www.linkedin.com/"),
]


def ask(values, args):
    for key, prompt, default in FIELDS:
        given = getattr(args, key.lower().replace("_url", ""), None)
        if given:
            values[key] = given
        elif args.yes:
            values[key] = default
        else:
            answer = input(f"{prompt} [{default}]: ").strip()
            values[key] = answer or default
    values["PHONE_LINK"] = values["PHONE"].replace(" ", "")
    return values


def fill(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name")
    parser.add_argument("--city")
    parser.add_argument("--email")
    parser.add_argument("--phone")
    parser.add_argument("--linkedin")
    parser.add_argument("--yes", action="store_true", help="don't ask; use placeholders for missing values")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    missing = [p for p in sorted(SCAFFOLD.rglob("*"))
               if p.is_file() and not (ROOT / p.relative_to(SCAFFOLD)).exists()]
    values = ask({}, args) if missing else {}

    created, skipped = [], 0
    for src in sorted(SCAFFOLD.rglob("*")):
        if not src.is_file():
            continue
        dst = ROOT / src.relative_to(SCAFFOLD)
        if dst.exists():
            skipped += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_SUFFIXES:
            dst.write_text(fill(src.read_text(encoding="utf-8"), values), encoding="utf-8")
        else:
            shutil.copy2(src, dst)
        created.append(dst.relative_to(ROOT).as_posix())

    for d in EMPTY_DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    print(f"Created {len(created)} file(s), kept {skipped} existing file(s).")
    for f in created:
        print("  +", f)

    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_index.py")], cwd=ROOT)

    print("\nNext steps:")
    print("  1. Put your CV, transcript and earlier letters in inbox/")
    print("  2. Open this folder in Claude Code and run: /ingest inbox/")
    print("  3. See TODO.md and README.md for the rest")


if __name__ == "__main__":
    main()
