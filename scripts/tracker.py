"""Edit tracker.md and the /find-jobs shortlist in the browser: filter, sort, change status, add and edit rows.

Usage: python scripts/tracker.py [--port 8765] [--no-browser] [--background photo.jpg]
Two tabs: Applications (tracker.md) and Job shortlist (jobs/shortlist.md, written by /find-jobs).
The page itself is scripts/tracker.html. For a photo behind the glass, pass --background or save one as
personal/dashboard-bg.jpg (or .png/.webp); without one, a soft gradient is used.
The files stay the source of truth, so Claude and the skills keep editing them as before. Every save
rewrites only the markdown table; text above and below it is kept. An edit is applied to the row as
it was when you opened it, on top of the latest file, so changes Claude made in the meantime survive.
Serves on 127.0.0.1 only. Stop with Ctrl+C.
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "tracker.md"
SHEETS = {"tracker": TRACKER, "jobs": ROOT / "jobs" / "shortlist.md"}
DEFAULT_STATUSES = {"tracker": ["drafted", "sent", "interview", "offer", "rejected", "no-reply"],
                    "jobs": ["new", "apply", "skip", "applied"]}
OPENABLE = {".pdf", ".tex", ".md", ".txt", ".docx"}  # never hand executables to the OS
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
PAGE = (Path(__file__).resolve().parent / "tracker.html").read_text(encoding="utf-8")
TOKEN = secrets.token_urlsafe(16)
PIPE = re.compile(r"(?<!\\)\|")


# ---------------------------------------------------------------------------
# Markdown table <-> rows
# ---------------------------------------------------------------------------

def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in PIPE.split(line)]


def is_separator(line):
    s = line.strip()
    return "-" in s and set(s) <= set("|-: ")


def parse(text, name="tracker.md"):
    """Split a markdown file into (lines before the table, columns, rows, lines after the table)."""
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        if lines[i].lstrip().startswith("|") and is_separator(lines[i + 1]):
            break
    else:
        raise ValueError(f"{name} has no markdown table")
    columns = split_row(lines[i])
    n, end, rows = len(columns), i + 2, []
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        cells = split_row(lines[end])
        if len(cells) > n:  # an unescaped | in the last cell: keep it as text
            cells = cells[:n - 1] + [" | ".join(cells[n - 1:])]
        rows.append(cells + [""] * (n - len(cells)))
        end += 1
    return lines[:i], columns, rows, lines[end:]


def cell(value):
    return " ".join(str(value).split()).replace("|", "\\|")


def render(head, columns, rows, tail, newline):
    table = ["| " + " | ".join(cell(c) for c in columns) + " |", "|" + "---|" * len(columns)]
    table += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return newline.join(head + table + tail) + newline


# ---------------------------------------------------------------------------
# Data for the page
# ---------------------------------------------------------------------------

def statuses(head, rows, status_col, default):
    """Status values from the 'Status: a → b → c / d' line above the table, plus any in use."""
    found = []
    for line in head:
        if line.lower().startswith("status:"):
            words = re.split(r"[→/,]", line.split(":", 1)[1].split(".")[0])
            found = [w.strip() for w in words if re.fullmatch(r"[a-z][a-z -]*", w.strip())]
    found = found or list(default)
    if status_col >= 0:
        found += [r[status_col] for r in rows if r[status_col] and r[status_col] not in found]
    return list(dict.fromkeys(found))


def tracks(rows, track_col):
    names = sorted(p.stem for p in (ROOT / "tracks").glob("*.md"))
    if track_col >= 0:
        names += sorted({r[track_col] for r in rows if r[track_col]} - set(names))
    return names


def openable(value):
    """The file or folder a tracker cell points to, if it exists inside this folder."""
    value = value.strip().strip("`")
    if not value:
        return None
    try:
        path = (ROOT / value).resolve()
        if not path.is_relative_to(ROOT) or not path.exists():
            return None
    except (OSError, ValueError):
        return None
    return path if path.is_dir() or path.suffix.lower() in OPENABLE else None


def find_col(columns, pattern):
    return next((i for i, c in enumerate(columns) if re.search(pattern, c, re.I)), -1)


def me():
    """Name and location for the page header, from profile/about-me.md once it's filled in."""
    path = ROOT / "profile" / "about-me.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    name = re.search(r"^- Name on CV:\s*([^(\n]+)", text, re.M)
    place = re.search(r"^- Location:\s*(.+)$", text, re.M)
    if not name or "{{" in name.group(1):
        return None
    return {"name": name.group(1).strip(), "location": place.group(1).strip() if place and "{{" not in place.group(1) else ""}


def load(sheet="tracker"):
    path = SHEETS[sheet]
    name = path.relative_to(ROOT).as_posix()
    base = {"sheet": sheet, "file": name, "me": me()}
    if not path.exists():
        return {**base, "missing": True}
    raw = path.read_bytes()
    head, columns, rows, tail = parse(raw.decode("utf-8"), name)
    status_col = find_col(columns, r"^status$")
    track_col = find_col(columns, r"^track$")
    link_col = find_col(columns, r"folder|file")
    return {
        **base,
        "hash": hashlib.sha1(raw).hexdigest(),
        "columns": columns,
        "rows": rows,
        "statuses": statuses(head, rows, status_col, DEFAULT_STATUSES[sheet]),
        "tracks": tracks(rows, track_col),
        "exists": [link_col >= 0 and openable(r[link_col]) is not None for r in rows],
        "tail": tail,  # shown read-only below the table (e.g. the shortlist's "Still to read")
    }


def save(body):
    sheet = body.get("sheet", "tracker")
    if sheet not in SHEETS:
        return 400, {"error": f"unknown sheet: {sheet}"}
    path = SHEETS[sheet]
    name = path.relative_to(ROOT).as_posix()
    if not path.exists():
        return 404, {"error": f"{name} not found"}
    raw = path.read_bytes()
    if hashlib.sha1(raw).hexdigest() != body.get("hash"):
        return 409, {"error": f"{name} changed on disk since the page loaded"}
    text = raw.decode("utf-8")
    head, columns, _, tail = parse(text, name)
    rows = body.get("rows")
    if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) != len(columns) for r in rows):
        return 400, {"error": f"every row needs exactly {len(columns)} cells"}
    newline = "\r\n" if "\r\n" in text else "\n"
    path.write_bytes(render(head, columns, rows, tail, newline).encode("utf-8"))
    return 200, load(sheet)


def open_path(value):
    path = openable(str(value))
    if path is None:
        return 404, {"error": f"not found in this folder: {value}"}
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
    return 200, {"ok": True}


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def trusted(self, post=False):
        # Host check blocks DNS rebinding; the token blocks other sites posting to this port.
        ok = self.headers.get("Host", "") in self.server.hosts
        return ok and (not post or self.headers.get("X-Token") == TOKEN)

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, {"error": "forbidden"})
        try:
            url = urlsplit(self.path)
            bg = self.server.background
            if url.path == "/":
                page = PAGE.replace("__TOKEN__", TOKEN).replace("__BG__", "1" if bg else "")
                return self.reply(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/background" and bg:
                return self.reply(200, bg.read_bytes(), IMAGE_TYPES[bg.suffix.lower()])
            if url.path == "/api/data":
                sheet = parse_qs(url.query).get("sheet", ["tracker"])[0]
                if sheet not in SHEETS:
                    return self.reply(400, {"error": f"unknown sheet: {sheet}"})
                return self.reply(200, load(sheet))
            self.reply(404, {"error": "not found"})
        except Exception as e:
            self.reply(500, {"error": str(e)})

    def do_POST(self):
        if not self.trusted(post=True):
            return self.reply(403, {"error": "forbidden"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/save":
                return self.reply(*save(body))
            if self.path == "/api/open":
                return self.reply(*open_path(body.get("path", "")))
            self.reply(404, {"error": "not found"})
        except Exception as e:
            self.reply(500, {"error": str(e)})


def serve(port):
    for p in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), Handler)
        except OSError:
            continue
        server.hosts = {f"127.0.0.1:{p}", f"localhost:{p}"}
        return server, p
    sys.exit(f"No free port in {port}-{port + 19}")


def background(arg):
    """The photo behind the glass: --background, else personal/dashboard-bg.*, else none (gradient)."""
    if arg:
        path = Path(arg).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in IMAGE_TYPES:
            sys.exit(f"--background must be an existing {'/'.join(IMAGE_TYPES)} file: {arg}")
        return path
    return next((p for ext in IMAGE_TYPES if (p := ROOT / "personal" / f"dashboard-bg{ext}").is_file()), None)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--background", help="photo shown blurred behind the dashboard")
    args = ap.parse_args()
    if not TRACKER.exists():
        sys.exit("tracker.md not found. Run `python scripts/init.py` first.")
    for sheet in SHEETS:
        load(sheet)  # fail early on a broken table
    server, port = serve(args.port)
    server.background = background(args.background)
    url = f"http://127.0.0.1:{port}/"
    print(f"Tracker: {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
