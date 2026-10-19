"""Search FINN, LinkedIn and NAV (arbeidsplassen.no) for job postings, and read one posting in full.

Usage:
    python scripts/find_jobs.py                           # run the saved searches, list postings to review
    python scripts/find_jobs.py --query "summer intern" --track quant    # add a one-off search to the run
    python scripts/find_jobs.py --list                    # list postings to review, without searching
    python scripts/find_jobs.py --done [--keep KEY ...]   # mark the listed postings as reviewed, except KEYs
    python scripts/find_jobs.py --show URL [URL ...]      # print postings in full (FINN, LinkedIn, NAV or any
                                                          # other page); several at once keeps LinkedIn paced

Saved searches live in jobs/searches.md (personal). jobs/seen.json remembers every posting found, so a
posting is listed until it's marked reviewed, and never again after that.
Indeed is not supported: it blocks automated requests. LinkedIn is read through its public (logged-out)
job listings. LinkedIn and NAV rate-limit quickly, so requests are spaced out and a run takes a few minutes.
A LinkedIn search with 0 results may have a location LinkedIn doesn't recognise: use its full name
("Amsterdam, North Holland, Netherlands", not "Amsterdam").
"""

import argparse
import base64
import html
import itertools
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "jobs"
SEARCHES = JOBS / "searches.md"
SEEN = JOBS / "seen.json"
SOURCES = ("finn", "linkedin", "nav")
DELAY = {"finn": 2, "linkedin": 15, "nav": 3, "other": 1}  # seconds between requests to one site
MAX_PAGES = {"finn": 2, "linkedin": 2, "nav": 1}  # FINN 50, LinkedIn 10, NAV 100 postings per page
KEEP_REVIEWED_DAYS = 120  # forget reviewed postings after this long (they're past the age limit anyway)
USER_AGENT = "CVizz personal job search (python urllib)"
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# HTTP and text helpers
# ---------------------------------------------------------------------------

class Blocked(Exception):
    """The site refused us (403, 999, or still 429 after waiting): skip it for the rest of the run."""


_last_request = {}


def fetch(url, site):
    for attempt in range(2):
        wait = DELAY[site] - (time.monotonic() - _last_request.get(site, -1e9))
        if wait > 0:
            time.sleep(wait + random.uniform(0, 1))
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                print(f"  {site}: rate-limited, waiting 60 s", file=sys.stderr)
                time.sleep(60)
                continue
            if e.code in (403, 429, 999):
                raise Blocked(f"HTTP {e.code}") from e
            raise
        finally:
            _last_request[site] = time.monotonic()


def html_to_text(fragment):
    fragment = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<li[^>]*>", "\n- ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|ul|ol|tr|dt|dd)>", "\n", fragment)
    fragment = re.sub(r"(?i)</?(strong|b|i|em|u|span|a|wbr|sup|sub|small|mark)\b[^>]*>", "", fragment)  # inline
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines()]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return re.sub(r"\n- *\n+", "\n- ", text).strip()


def first(pattern, text):
    m = re.search(pattern, text, re.S)
    return html_to_text(m.group(1)) if m else ""


def day(ms):
    return datetime.fromtimestamp(ms / 1000).date().isoformat() if ms else ""


def parse_deadline(text):
    """NAV writes deadlines as ISO dates, dd.mm.yyyy or free text ('Snarest')."""
    text = (text or "").strip()
    if m := re.match(r"(\d{4})-(\d{2})-(\d{2})", text):
        return "-".join(m.groups())
    if m := re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text):
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return text


def fingerprint(p):
    """Same company + same title = same posting, whichever site it came from."""
    def words(s):
        return re.sub(r"[^a-z0-9æøå]+", " ", s.lower()).split()
    company = [w for w in words(p["company"]) if w not in {"as", "asa", "ab", "the"}]
    return f"{company[0] if company else ''}|{' '.join(words(p['title']))}"


# ---------------------------------------------------------------------------
# Sources: each yields pages (lists) of postings, newest first
# ---------------------------------------------------------------------------

def finn_pages(search, max_age):
    for page in itertools.count(1):
        url = "https://www.finn.no/job/search?" + urllib.parse.urlencode(
            {"q": search["query"], "sort": "PUBLISHED_DESC", "page": page})
        m = re.search(r"<script[^>]*data-react-query-state[^>]*>(.*?)</script>", fetch(url, "finn"), re.S)
        if not m:
            raise ValueError("FINN page format changed (no search data found)")
        state = json.loads(base64.b64decode(m.group(1)))
        data = next((q["state"]["data"] for q in state.get("queries", [])
                     if isinstance(q.get("state", {}).get("data"), dict) and "docs" in q["state"]["data"]), None)
        if data is None:
            raise ValueError("FINN page format changed (no result list found)")
        yield [{
            "key": f"finn:{d['id']}",
            "source": "finn",
            "title": d.get("heading") or d.get("job_title") or "",
            "company": d.get("company_name") or "",
            "location": d.get("location") or "",
            "published": day(d.get("published") or d.get("timestamp")),
            "deadline": day(d.get("deadline")),
            "url": d.get("canonical_url") or f"https://www.finn.no/job/ad/{d['id']}",
        } for d in data["docs"] if d.get("type", "job") == "job"]
        paging = data.get("metadata", {}).get("paging", {})
        if paging.get("current", page) >= paging.get("last", page):
            return


def linkedin_pages(search, max_age):
    for start in itertools.count(0, 10):
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode({
            "keywords": search["query"], "location": search.get("location") or "Norway",
            "f_TPR": f"r{max_age * 86400}", "sortBy": "DD", "start": start})
        cards = fetch(url, "linkedin").split('data-entity-urn="urn:li:jobPosting:')[1:]
        if not cards:
            return
        page = []
        for card in cards:
            job_id = re.match(r"\d+", card).group(0)
            page.append({
                "key": f"linkedin:{job_id}",
                "source": "linkedin",
                "title": first(r"base-search-card__title[^>]*>(.*?)</h3>", card),
                "company": first(r"base-search-card__subtitle[^>]*>(.*?)</h4>", card),
                "location": first(r"job-search-card__location[^>]*>(.*?)</span>", card),
                "published": (re.search(r'<time[^>]*datetime="([\d-]+)"', card) or [None, ""])[1],
                "deadline": "",
                "url": f"https://www.linkedin.com/jobs/view/{job_id}",
            })
        yield page


def nav_pages(search, max_age):
    url = "https://arbeidsplassen.nav.no/stillinger/api/search?" + urllib.parse.urlencode(
        {"q": search["query"], "from": 0, "size": 100, "sort": "published"})
    page = []
    for hit in json.loads(fetch(url, "nav"))["hits"]["hits"]:
        s = hit["_source"]
        if s.get("status", "ACTIVE") != "ACTIVE":
            continue
        place = (s.get("locationList") or [{}])[0]
        ref = str(s.get("reference") or "")
        if s.get("source") == "FINN" and ref.isdigit():  # NAV mirrors FINN ads: use FINN's id and link
            key, link = f"finn:{ref}", f"https://www.finn.no/job/ad/{ref}"
        else:
            key, link = f"nav:{s['uuid']}", f"https://arbeidsplassen.nav.no/stillinger/stilling/{s['uuid']}"
        page.append({
            "key": key,
            "source": "nav",
            "title": s.get("title") or "",
            "company": s.get("businessName") or (s.get("employer") or {}).get("name") or "",
            "location": (place.get("city") or place.get("county") or place.get("country") or "").title(),
            "published": (s.get("published") or "")[:10],
            "deadline": parse_deadline((s.get("properties") or {}).get("applicationdue")),
            "url": link,
        })
    yield page


PAGES = {"finn": finn_pages, "linkedin": linkedin_pages, "nav": nav_pages}


# ---------------------------------------------------------------------------
# Searching and the seen list
# ---------------------------------------------------------------------------

def load_config():
    if not SEARCHES.exists():
        sys.exit("No jobs/searches.md. Run: python scripts/init.py")
    text = SEARCHES.read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.exit("jobs/searches.md needs YAML frontmatter between --- lines")
    try:
        return yaml.safe_load(text.split("---", 2)[1]) or {}
    except yaml.YAMLError as e:
        sys.exit(f"ERROR: invalid frontmatter in jobs/searches.md: {e}")


def load_seen():
    if SEEN.exists():
        return json.loads(SEEN.read_text(encoding="utf-8"))
    return {"last_run": "", "postings": {}}


def save_seen(seen):
    cutoff = (date.today() - timedelta(days=KEEP_REVIEWED_DAYS)).isoformat()
    seen["postings"] = {k: p for k, p in seen["postings"].items()
                        if p["status"] == "new" or p["first_seen"] >= cutoff}
    JOBS.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")


def run_searches(config, seen):
    max_age = int(config.get("max_age_days") or 30)
    today = date.today().isoformat()
    oldest = (date.today() - timedelta(days=max_age)).isoformat()
    exclude = [w.lower() for w in config.get("exclude_title") or []]
    known = set(seen["postings"])  # before this run: paging stops once a page reaches these
    prints = {fingerprint(p): k for k, p in seen["postings"].items()}
    blocked, rows = {}, []

    def wanted(p):
        return not ((p["published"] and p["published"] < oldest)
                    or (ISO_DATE.match(p["deadline"]) and p["deadline"] < today)
                    or any(w in p["title"].lower() for w in exclude))

    for search in config.get("searches") or []:
        for source in search.get("sources") or SOURCES:
            if source not in PAGES:
                rows.append((source, search["query"], "unknown source"))
                continue
            if source in blocked:
                continue
            found = new = 0
            try:
                for n, page in enumerate(PAGES[source](search, max_age), 1):
                    found += len(page)
                    for p in filter(wanted, page):
                        fp = fingerprint(p)
                        if p["key"] in seen["postings"] or fp in prints:
                            continue
                        p.update(track=search.get("track", ""), query=search["query"],
                                 first_seen=today, status="new")
                        seen["postings"][p["key"]] = p
                        prints[fp] = p["key"]
                        new += 1
                    if n >= MAX_PAGES[source] or any(
                            p["key"] in known or (p["published"] and p["published"] < oldest) for p in page):
                        break
                rows.append((source, search["query"], f"{found} found, {new} new"))
            except Blocked as e:
                blocked[source] = str(e)
                rows.append((source, search["query"], f"BLOCKED ({e}): skipped for the rest of this run"))
            except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as e:
                rows.append((source, search["query"], f"FAILED: {e}"))
    seen["last_run"] = today
    return rows


def pending(seen):
    today = date.today().isoformat()
    for p in seen["postings"].values():
        if p["status"] == "new" and ISO_DATE.match(p["deadline"]) and p["deadline"] < today:
            p["status"] = "expired"
    rows = [p for p in seen["postings"].values() if p["status"] == "new"]
    rows.sort(key=lambda p: p["published"], reverse=True)  # newest first within the same deadline
    rows.sort(key=lambda p: p["deadline"] if ISO_DATE.match(p["deadline"]) else "9999")
    return rows


def print_pending(seen):
    rows = pending(seen)
    print(f"\n{len(rows)} posting(s) to review, soonest deadline first:")
    print("key | deadline | published | company | title | location | track | url")
    for p in rows:
        print(" | ".join([p["key"], p["deadline"] or "-", p["published"] or "-", p["company"], p["title"],
                          p["location"], p["track"], p["url"]]))


# ---------------------------------------------------------------------------
# Reading one posting
# ---------------------------------------------------------------------------

def find_job_posting(obj):
    if isinstance(obj, dict):
        if obj.get("@type") == "JobPosting":
            return obj
        obj = list(obj.values())
    if isinstance(obj, list):
        return next((j for j in map(find_job_posting, obj) if j), None)
    return None


def show(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if "linkedin.com" in host:
        m = re.search(r"(?:currentJobId=|/view/(?:[^/?]*-)?)(\d{6,})", url)
        if not m:
            sys.exit("Couldn't find a job id in that LinkedIn link")
        page = fetch(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}", "linkedin")
        print(first(r"top-card-layout__title[^>]*>(.*?)</h2>", page))
        print(first(r"topcard__org-name-link[^>]*>(.*?)</a>", page), "·",
              first(r"topcard__flavor--bullet[^>]*>(.*?)</span>", page), "·",
              first(r"posted-time-ago__text[^>]*>(.*?)</span>", page))
        criteria = re.findall(r"job-criteria-subheader[^>]*>(.*?)</h3>.*?job-criteria-text[^>]*>(.*?)</span>",
                              page, re.S)
        print(" · ".join(f"{html_to_text(k)}: {html_to_text(v)}" for k, v in criteria))
        print("\n" + first(r"show-more-less-html__markup[^>]*>(.*?)</div>", page))
        return
    site = "finn" if "finn.no" in host else "nav" if "nav.no" in host else "other"
    page = fetch(url, site)
    for m in re.finditer(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", page, re.S):
        try:
            job = find_job_posting(json.loads(m.group(1)))
        except json.JSONDecodeError:
            continue
        if job:
            org = job.get("hiringOrganization") or {}
            places = job.get("jobLocation") or []
            places = places if isinstance(places, list) else [places]
            where = ", ".join(filter(None, ((pl.get("address") or {}).get("addressLocality") for pl in places)))
            print(job.get("title", ""))
            print(org.get("name", "") if isinstance(org, dict) else org, "·", where,
                  "· posted", str(job.get("datePosted", ""))[:10], "· deadline", str(job.get("validThrough", ""))[:10])
            print("\n" + html_to_text(html.unescape(job.get("description", ""))))
            return
    m = re.search(r"(?is)<main[^>]*>(.*?)</main>", page) or re.search(r"(?is)<body[^>]*>(.*?)</body>", page)
    text = html_to_text(m.group(1) if m else page)
    print(text[:20000] + ("\n[... cut at 20,000 characters]" if len(text) > 20000 else ""))


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", help="one-off search, run on top of the saved searches")
    parser.add_argument("--track", default="", help="track label for --query")
    parser.add_argument("--sources", nargs="+", choices=SOURCES, help="sources for --query (default: all)")
    parser.add_argument("--location", help="LinkedIn location for --query (default: Norway)")
    parser.add_argument("--only", action="store_true", help="run only --query, not the saved searches")
    parser.add_argument("--list", action="store_true", help="list postings to review, without searching")
    parser.add_argument("--done", action="store_true", help="mark the listed postings as reviewed")
    parser.add_argument("--keep", nargs="+", default=[], metavar="KEY", help="with --done: leave these listed")
    parser.add_argument("--show", nargs="+", metavar="URL", help="print postings in full (paced like a search)")
    args = parser.parse_args()

    if args.show:
        for n, url in enumerate(args.show):
            print(f"{'=' * 100}\n{url}\n" if len(args.show) > 1 else "", end="")
            try:
                show(url)
            except (Blocked, urllib.error.URLError, TimeoutError) as e:
                print(f"Couldn't read {url}: {e}")
            if n < len(args.show) - 1:
                print()
        return

    seen = load_seen()
    if args.done:
        keep = set(args.keep)
        marked = [p for p in pending(seen) if p["key"] not in keep]
        for p in marked:
            p["status"] = "reviewed"
        save_seen(seen)
        print(f"Marked {len(marked)} posting(s) as reviewed; {len(pending(seen))} still to review.")
        return

    if not args.list:
        config = load_config()
        if args.query:
            extra = {"query": args.query, "track": args.track, "sources": args.sources, "location": args.location}
            config["searches"] = ([] if args.only else config.get("searches") or []) + [extra]
        try:
            rows = run_searches(config, seen)
        finally:
            save_seen(seen)
        print("Searches:")
        for source, query, result in rows:
            print(f"  {source:<8} {query!r}: {result}")
    print_pending(seen)
    save_seen(seen)


if __name__ == "__main__":
    main()
