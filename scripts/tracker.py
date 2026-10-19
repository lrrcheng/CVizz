"""Edit tracker.md in the browser: filter, sort, change status, add and edit applications.

Usage: python scripts/tracker.py [--port 8765] [--no-browser]
tracker.md stays the source of truth, so Claude and the skills keep editing it as before. Every save
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

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "tracker.md"
DEFAULT_STATUSES = ["drafted", "sent", "interview", "offer", "rejected", "no-reply"]
OPENABLE = {".pdf", ".tex", ".md", ".txt", ".docx"}  # never hand executables to the OS
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


def parse(text):
    """Split tracker.md into (lines before the table, columns, rows, lines after the table)."""
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        if lines[i].lstrip().startswith("|") and is_separator(lines[i + 1]):
            break
    else:
        raise ValueError("tracker.md has no markdown table")
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

def statuses(head, rows, status_col):
    """Status values from the 'Status: a → b → c / d' line above the table, plus any in use."""
    found = []
    for line in head:
        if line.lower().startswith("status:"):
            words = re.split(r"[→/,]", line.split(":", 1)[1].split(".")[0])
            found = [w.strip() for w in words if re.fullmatch(r"[a-z][a-z -]*", w.strip())]
    found = found or list(DEFAULT_STATUSES)
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


def load():
    raw = TRACKER.read_bytes()
    head, columns, rows, _ = parse(raw.decode("utf-8"))
    status_col = find_col(columns, r"^status$")
    track_col = find_col(columns, r"^track$")
    link_col = find_col(columns, r"folder|file")
    return {
        "hash": hashlib.sha1(raw).hexdigest(),
        "columns": columns,
        "rows": rows,
        "statuses": statuses(head, rows, status_col),
        "tracks": tracks(rows, track_col),
        "exists": [link_col >= 0 and openable(r[link_col]) is not None for r in rows],
    }


def save(body):
    raw = TRACKER.read_bytes()
    if hashlib.sha1(raw).hexdigest() != body.get("hash"):
        return 409, {"error": "tracker.md changed on disk since the page loaded"}
    text = raw.decode("utf-8")
    head, columns, _, tail = parse(text)
    rows = body.get("rows")
    if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) != len(columns) for r in rows):
        return 400, {"error": f"every row needs exactly {len(columns)} cells"}
    newline = "\r\n" if "\r\n" in text else "\n"
    TRACKER.write_bytes(render(head, columns, rows, tail, newline).encode("utf-8"))
    return 200, load()


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
            if self.path == "/":
                return self.reply(200, PAGE.replace("__TOKEN__", TOKEN).encode("utf-8"), "text/html; charset=utf-8")
            if self.path == "/api/data":
                return self.reply(200, load())
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


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if not TRACKER.exists():
        sys.exit("tracker.md not found. Run `python scripts/init.py` first.")
    load()  # fail early on a broken table
    server, port = serve(args.port)
    url = f"http://127.0.0.1:{port}/"
    print(f"Tracker: {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Application tracker</title>
<style>
  :root {
    --bg: #f7f7f5; --panel: #ffffff; --text: #1d1d1b; --muted: #6b6b66; --line: #e4e4df;
    --hover: #f0f0ec; --accent: #2f5bd3; --accent-text: #ffffff; --danger: #c0392b;
    --shadow: 0 10px 40px rgba(0,0,0,.18);
    --s-drafted: #8a6100; --s-drafted-bg: #fdf1d6;
    --s-sent: #1f4fbf; --s-sent-bg: #e3ebff;
    --s-interview: #6b36b8; --s-interview-bg: #efe5ff;
    --s-offer: #1d7a3e; --s-offer-bg: #dcf3e3;
    --s-rejected: #b02a2a; --s-rejected-bg: #fde3e3;
    --s-other: #5c5c57; --s-other-bg: #ececea;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #161615; --panel: #1f1f1d; --text: #ecece8; --muted: #9a9a93; --line: #33332f;
      --hover: #272724; --accent: #6f93ff; --accent-text: #0b1020; --danger: #ff7b6e;
      --shadow: 0 10px 40px rgba(0,0,0,.5);
      --s-drafted: #f2c766; --s-drafted-bg: #3a2f14;
      --s-sent: #9db8ff; --s-sent-bg: #1e2a4a;
      --s-interview: #c9a6ff; --s-interview-bg: #31234a;
      --s-offer: #7fd99c; --s-offer-bg: #17361f;
      --s-rejected: #ff9a9a; --s-rejected-bg: #431d1d;
      --s-other: #b9b9b2; --s-other-bg: #2c2c29;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 1500px; margin: 0 auto; padding: 24px 16px 64px; }
  h1 { font-size: 22px; margin: 0 0 14px; font-weight: 650; }
  button, input, select, textarea { font: inherit; color: inherit; }
  button { cursor: pointer; border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 6px 12px; }
  button:hover { background: var(--hover); }
  button.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-text); font-weight: 600; }
  button.danger { color: var(--danger); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
  .chip { border-radius: 999px; padding: 4px 12px; font-size: 13px; }
  .chip b { font-weight: 650; margin-left: 4px; }
  .chip.zero { opacity: .5; }
  .chip.on { outline: 2px solid var(--accent); outline-offset: 1px; }
  .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }
  .toolbar input[type=search] { flex: 1 1 260px; min-width: 0; }
  .toolbar .spacer { flex: 1; }
  input, select, textarea { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; }
  input:focus, select:focus, textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; border-color: transparent; }
  .wrap { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; vertical-align: top; padding: 9px 12px; border-bottom: 1px solid var(--line); }
  th { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); font-weight: 600;
       cursor: pointer; user-select: none; white-space: nowrap; position: sticky; top: 0; background: var(--panel); }
  th .arrow { margin-left: 4px; }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: var(--hover); }
  tbody tr:last-child td { border-bottom: 0; }
  td.k-date { white-space: nowrap; color: var(--muted); font-variant-numeric: tabular-nums; }
  td.k-long { min-width: 240px; }
  td.k-text { min-width: 110px; }
  td.k-link { min-width: 150px; }
  .clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  td.k-notes .clamp { color: var(--muted); }
  .pill { appearance: none; -webkit-appearance: none; border: 0; border-radius: 999px; padding: 3px 12px;
          font-size: 12.5px; font-weight: 600; cursor: pointer; }
  .pill, .chip { color: var(--s-other); background: var(--s-other-bg); }
  .s-drafted { color: var(--s-drafted); background: var(--s-drafted-bg); }
  .s-sent { color: var(--s-sent); background: var(--s-sent-bg); }
  .s-interview { color: var(--s-interview); background: var(--s-interview-bg); }
  .s-offer { color: var(--s-offer); background: var(--s-offer-bg); }
  .s-rejected { color: var(--s-rejected); background: var(--s-rejected-bg); }
  .chip.all { color: var(--text); background: var(--panel); border: 1px solid var(--line); }
  .link { display: flex; gap: 8px; align-items: center; }
  .link button { padding: 2px 10px; font-size: 12.5px; white-space: nowrap; }
  .link span { overflow-wrap: anywhere; }
  .missing { color: var(--muted); font-style: italic; overflow-wrap: anywhere; }
  .empty { padding: 32px; text-align: center; color: var(--muted); }
  .hint { color: var(--muted); font-size: 12.5px; margin-top: 10px; }
  kbd { border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 4px; padding: 0 5px; font-size: 11.5px; }
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,.28); }
  .drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(580px, 100vw); background: var(--panel);
            box-shadow: var(--shadow); display: flex; flex-direction: column; }
  .drawer header { padding: 18px 20px 6px; }
  .drawer h2 { margin: 0; font-size: 18px; }
  .drawer form { flex: 1; overflow-y: auto; padding: 10px 20px; display: grid; gap: 14px; align-content: start; }
  .drawer label { display: grid; gap: 5px; font-size: 12px; text-transform: uppercase; letter-spacing: .04em;
                  color: var(--muted); font-weight: 600; }
  .drawer label > * { text-transform: none; letter-spacing: 0; font-size: 14px; font-weight: 400; color: var(--text); }
  .drawer textarea { resize: vertical; min-height: 64px; }
  .drawer .row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .drawer .inline { display: flex; gap: 8px; }
  .drawer .inline input { flex: 1; min-width: 0; }
  .drawer footer { display: flex; gap: 8px; padding: 14px 20px; border-top: 1px solid var(--line); }
  .drawer footer .spacer { flex: 1; }
  .toast { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); background: var(--text);
           color: var(--bg); padding: 9px 16px; border-radius: 10px; box-shadow: var(--shadow); max-width: 90vw; }
  .toast.error { background: var(--danger); color: #fff; }
  [hidden] { display: none !important; }
  @media (max-width: 640px) { .drawer .row { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<main>
  <h1>Applications</h1>
  <div class="chips" id="chips"></div>
  <div class="toolbar">
    <input type="search" id="search" placeholder="Search company, role, notes…   ( / )">
    <select id="trackFilter"></select>
    <span class="spacer"></span>
    <button id="reload" title="Reload tracker.md from disk">Reload</button>
    <button id="add" class="primary">+ Add application</button>
  </div>
  <div class="wrap">
    <table><thead id="head"></thead><tbody id="body"></tbody></table>
    <div class="empty" id="empty" hidden>No applications match.</div>
  </div>
  <div class="hint">Saves straight to <code>tracker.md</code>. Click a row to edit it. Click a column title to sort.
    <kbd>Ctrl</kbd>+<kbd>S</kbd> saves the form, <kbd>Esc</kbd> closes it.</div>
</main>

<div class="overlay" id="overlay" hidden></div>
<aside class="drawer" id="drawer" hidden>
  <header><h2 id="drawerTitle"></h2></header>
  <form id="form" autocomplete="off"></form>
  <footer>
    <button type="button" class="danger" id="delete">Delete</button>
    <span class="spacer"></span>
    <button type="button" id="cancel">Cancel</button>
    <button type="button" class="primary" id="save">Save</button>
  </footer>
</aside>
<div class="toast" id="toast" hidden></div>

<script>
const TOKEN = "__TOKEN__";
const $ = (id) => document.getElementById(id);
const state = { data: null, status: "", track: "", q: "", sort: -1, dir: 1, original: undefined };

function el(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n[k] = v;
  }
  for (const k of kids) if (k != null) n.append(k);
  return n;
}
const slug = (s) => "s-" + String(s).toLowerCase().replace(/[^a-z]+/g, "-");
const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

function kind(i) {
  const c = state.data.columns[i].toLowerCase();
  if (c === "status") return "status";
  if (c === "track") return "track";
  if (/date|deadline/.test(c)) return "date";
  if (/folder|file/.test(c)) return "link";
  if (/note/.test(c)) return "notes";
  if (/role|title|position|comment/.test(c)) return "long";
  return "text";
}
const colOf = (k) => state.data.columns.findIndex((_, i) => kind(i) === k);

let toastTimer;
function toast(msg, error = false) {
  const t = $("toast");
  t.textContent = msg; t.className = "toast" + (error ? " error" : ""); t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), error ? 6000 : 2200);
}

async function api(path, body) {
  const opts = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Token": TOKEN }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  const json = await res.json().catch(() => ({ error: res.statusText }));
  if (!res.ok) { const e = new Error(json.error || res.statusText); e.status = res.status; throw e; }
  return json;
}

async function refresh(quiet = false) {
  try { state.data = await api("/api/data"); render(); if (!quiet) toast("Reloaded"); }
  catch (e) { toast(e.message, true); }
}

// Apply one edit to the row as it was when opened. If the file changed on disk meanwhile,
// reload and re-apply on top of the latest version (unless that very row was changed).
async function commit(original, updated) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const rows = state.data.rows.map((r) => [...r]);
    const i = original ? rows.findIndex((r) => same(r, original)) : -1;
    if (original && i < 0) {
      render();
      toast("This application was changed on disk in the meantime. Reloaded; please make your edit again.", true);
      return false;
    }
    if (updated === null) rows.splice(i, 1); else if (i < 0) rows.push(updated); else rows[i] = updated;
    try {
      state.data = await api("/api/save", { hash: state.data.hash, rows });
      render(); toast(updated === null ? "Deleted" : "Saved");
      return true;
    } catch (e) {
      if (e.status !== 409 || attempt) { toast(e.message, true); return false; }
      try { state.data = await api("/api/data"); } catch (e2) { toast(e2.message, true); return false; }
    }
  }
}

// ---------------------------------------------------------------- table
function render() {
  renderChips(); renderTrackFilter(); renderHead(); renderBody();
}

function renderChips() {
  const s = colOf("status"), chips = $("chips");
  chips.replaceChildren();
  if (s < 0) return;
  const rows = state.data.rows;
  chips.append(el("button", { class: "chip all" + (state.status === "" ? " on" : ""),
    onclick: () => { state.status = ""; render(); } }, "All", el("b", {}, String(rows.length))));
  for (const st of state.data.statuses) {
    const n = rows.filter((r) => r[s] === st).length;
    chips.append(el("button", { class: `chip ${slug(st)}` + (n ? "" : " zero") + (state.status === st ? " on" : ""),
      onclick: () => { state.status = state.status === st ? "" : st; render(); } }, st, el("b", {}, String(n))));
  }
}

function renderTrackFilter() {
  const sel = $("trackFilter"), t = colOf("track");
  sel.hidden = t < 0;
  sel.replaceChildren(el("option", { value: "" }, "All tracks"),
    ...state.data.tracks.map((x) => el("option", { value: x }, x)));
  sel.value = state.track;
}

function renderHead() {
  $("head").replaceChildren(el("tr", {}, ...state.data.columns.map((c, i) => el("th", {
    onclick: () => {
      if (state.sort !== i) { state.sort = i; state.dir = 1; }
      else if (state.dir === 1) state.dir = -1;
      else state.sort = -1;
      renderHead(); renderBody();
    } }, c, state.sort === i ? el("span", { class: "arrow" }, state.dir === 1 ? "▲" : "▼") : null))));
}

function visibleRows() {
  const { rows } = state.data, s = colOf("status"), t = colOf("track"), q = state.q.toLowerCase();
  let list = rows.map((r, i) => ({ r, i })).filter(({ r }) =>
    (!state.status || r[s] === state.status) && (!state.track || r[t] === state.track) &&
    (!q || r.some((v) => v.toLowerCase().includes(q))));
  if (state.sort >= 0) {
    const k = state.sort;
    list.sort((a, b) => state.dir * a.r[k].localeCompare(b.r[k], undefined, { numeric: true, sensitivity: "base" }));
  }
  return list;
}

function renderBody() {
  const list = visibleRows();
  $("empty").hidden = list.length > 0;
  $("body").replaceChildren(...list.map(({ r, i }) => el("tr", { onclick: () => openDrawer(r) },
    ...r.map((v, c) => el("td", { class: "k-" + kind(c) }, cellContent(r, i, c, v))))));
}

function cellContent(row, i, c, v) {
  const k = kind(c);
  if (k === "status") {
    const sel = el("select", { class: "pill " + slug(v), title: "Change status",
      onclick: (e) => e.stopPropagation(),
      onchange: (e) => { const next = [...row]; next[c] = e.target.value; commit(row, next); } },
      ...statusOptions(v));
    sel.value = v;
    return sel;
  }
  if (k === "link") {
    if (!v) return "";
    if (!state.data.exists[i]) return el("span", { class: "missing", title: "Not found in this folder" }, v);
    const name = v.replace(/[\\/]+$/, "").split(/[\\/]/).pop();
    return el("div", { class: "link" },
      el("button", { title: "Open " + v, onclick: (e) => { e.stopPropagation(); openPath(v); } }, "Open"),
      el("span", { title: v }, name));
  }
  if (k === "long" || k === "notes") return el("div", { class: "clamp", title: v }, v);
  return v;
}

function statusOptions(current) {
  const list = [...state.data.statuses];
  if (current && !list.includes(current)) list.push(current);
  if (!current) list.unshift("");
  return list.map((s) => el("option", { value: s }, s || "—"));
}

async function openPath(v) {
  try { await api("/api/open", { path: v }); } catch (e) { toast(e.message, true); }
}

// ---------------------------------------------------------------- drawer
function openDrawer(row) {
  const d = state.data, isNew = !row;
  state.original = row || null;
  const values = row ? [...row] : d.columns.map((_, i) =>
    kind(i) === "date" && /^date$/i.test(d.columns[i]) ? today() : kind(i) === "status" ? d.statuses[0] || "" : "");
  $("drawerTitle").textContent = isNew ? "New application"
    : [row[d.columns.findIndex((c) => /company/i.test(c))], row[d.columns.findIndex((c) => /role/i.test(c))]]
        .filter(Boolean).join(" · ") || "Edit application";
  $("delete").hidden = isNew;

  const fields = d.columns.map((c, i) => field(c, i, values[i]));
  const form = $("form");
  form.replaceChildren();
  // pair up short fields two per line, long ones on their own
  for (let i = 0; i < fields.length; i++) {
    const k = kind(i), next = i + 1 < fields.length ? kind(i + 1) : null;
    const short = (x) => ["date", "status", "track", "text"].includes(x);
    if (short(k) && short(next) && k !== "text") { form.append(el("div", { class: "row" }, fields[i], fields[i + 1])); i++; }
    else form.append(fields[i]);
  }
  $("overlay").hidden = false; $("drawer").hidden = false;
  const first = form.querySelector("input, textarea, select");
  if (first) first.focus();
}

function field(name, i, value) {
  const k = kind(i), id = "f" + i;
  let input;
  if (k === "status") {
    input = el("select", { id }, ...statusOptions(value));
    input.value = value;
  } else if (k === "track") {
    input = el("input", { id, value });
    input.setAttribute("list", "trackList");
    return el("label", {}, name, input,
      el("datalist", { id: "trackList" }, ...state.data.tracks.map((t) => el("option", { value: t }))));
  } else if (k === "date") {
    input = el("input", { id, type: /^\d{4}-\d{2}-\d{2}$/.test(value) || !value ? "date" : "text", value });
  } else if (k === "notes" || k === "long") {
    input = el("textarea", { id, value, rows: k === "notes" ? 7 : 2 });
  } else if (k === "link") {
    input = el("input", { id, value, placeholder: "applications/2026-10-company-role/" });
    return el("label", {}, name, el("div", { class: "inline" }, input,
      el("button", { type: "button", onclick: () => openPath(input.value) }, "Open")));
  } else {
    input = el("input", { id, value });
  }
  return el("label", {}, name, input);
}

function closeDrawer() {
  $("overlay").hidden = true; $("drawer").hidden = true; state.original = undefined;
}

async function saveDrawer() {
  const values = state.data.columns.map((_, i) => ($("f" + i).value || "").trim());
  if (state.original && same(values, state.original)) return closeDrawer();
  if (values.every((v) => !v)) return toast("Fill in at least one field.", true);
  if (await commit(state.original, values)) closeDrawer();
}

async function deleteRow() {
  if (!state.original || !confirm("Delete this application from tracker.md?")) return;
  if (await commit(state.original, null)) closeDrawer();
}

// ---------------------------------------------------------------- wiring
$("search").addEventListener("input", (e) => { state.q = e.target.value; renderBody(); });
$("trackFilter").addEventListener("change", (e) => { state.track = e.target.value; renderBody(); });
$("reload").addEventListener("click", () => refresh());
$("add").addEventListener("click", () => openDrawer(null));
$("save").addEventListener("click", saveDrawer);
$("cancel").addEventListener("click", closeDrawer);
$("delete").addEventListener("click", deleteRow);
$("overlay").addEventListener("click", closeDrawer);
$("form").addEventListener("submit", (e) => { e.preventDefault(); saveDrawer(); });
document.addEventListener("keydown", (e) => {
  const open = !$("drawer").hidden;
  if (e.key === "Escape" && open) closeDrawer();
  else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s" && open) { e.preventDefault(); saveDrawer(); }
  else if (e.key === "/" && !open && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
    e.preventDefault(); $("search").focus();
  }
});
// pick up edits Claude made to tracker.md while the tab was in the background
window.addEventListener("focus", () => { if ($("drawer").hidden) refresh(true); });
refresh(true);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
