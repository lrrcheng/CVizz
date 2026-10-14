# Job application system

This folder produces tailored, accurate CVs and cover letters for the user, and gradually builds
a complete, verified picture of their experience. Who the user is (name, contact details, studies,
languages) is in `profile/about-me.md`; how they want to write is in `profile/style.md`.
Career directions are defined as tracks in `tracks/`.

At the start of a session, read `PROJECT-STATE.md` (current situation, decisions, gotchas; personal,
may not exist on a fresh install) and then `TODO.md`. Update `PROJECT-STATE.md` at the end of any
session that changes the state. Do open items in the Claude section when relevant,
and tick items off (or add new ones) as things are resolved. `README.md` is the human guide:
keep it in sync when the workflow changes. If `profile/` is missing, tell the user to run
`python scripts/init.py` first.

## Layout
```
profile/                 PERSONAL (gitignored)
  experiences/*.md       one entry per job/project/education/award group; facts live here
  skills.md              the ONLY allowed tags, with synonyms
  about-me.md            contact, languages, interests (never store ID numbers or address)
  motivation.md          goals and "why this field" material (only from the user's own words)
  style.md               writing rules; updated by /sync and by feedback
  sources.md             register of every source ID used in `src:`, incl. archive folders
tracks/*.md              per-track priorities, required tags, CV rules, translation maps
base/                    master CVs per variant (cv-technical.tex, cv-quant.tex, cv-finance.tex)
applications/<YYYY-MM-company-role>/   one folder per application
companies/               notes per company, reused across applications
generated/               output of scripts/build_index.py; NEVER edit by hand
inbox/                   new material to ingest; move files to inbox/processed/ once ingested
tracker.md, TODO.md      application overview and open tasks
personal/                the user's own resources (diplomas, transcripts, references, old CVs), any
                         subfolders; a source library for /ingest, registered in profile/sources.md

templates/               SHARED: cv.cls, coverletter.cls (all layout lives here)
scripts/                 SHARED: init.py, build_index.py, build_pdf.py
scaffold/                SHARED: starter versions of every personal file (used by init.py)
.claude/skills/          SHARED: /apply, /interview, /sync, /ingest, /interview-prep
```
Everything marked PERSONAL is gitignored. `.ignore` re-enables these paths for search (Grep),
so use Grep/Glob on them normally. Never move personal data into shared files
(CLAUDE.md, README.md, scripts, templates, scaffold, skills).

## The non-negotiable rule: no invented facts
- Every claim in a CV or letter must trace to a fact line in `profile/experiences/`.
- Fact line format (the indexer parses it exactly):
  `- F<n> [tag, tag] Text of the fact · <verified|stated|unverified> · src: <source-id>`
  - `verified`: confirmed by the user or by a document (transcript, contract, reference, git history).
  - `stated`: from the user's own CV or letters; usable, but confirm if it's central to an application.
  - `unverified`: inconsistent or uncertain; NEVER use in a draft until confirmed.
- Rephrasing and reframing is allowed (see each track's translation map); adding substance is not.
  If a posting asks for something with no evidence, ASK. Do not stretch.
- Skills the posting asks for follow the rules in `profile/style.md` ("Skills the posting asks for").
- In .tex files, end each bullet with a comment `% src: <entry-id>#F<n>` so text stays traceable.
- Numbers (accuracy, users, money, grades) must match the fact exactly.
- Backtest/trading results: never quote a best-of-N Sharpe or return; describe method and controls.

## Retrieval procedure (use for every application)
1. Read `generated/INDEX.md`, `profile/skills.md` and the relevant `tracks/<track>.md`.
2. Map EVERY requirement and task in the posting to tags. Use
   `python scripts/build_index.py --find "<phrase>" "<phrase>" ...` to resolve phrases via synonyms
   and list matching facts. A phrase with no tag match → add a synonym or new tag to skills.md.
3. Read the 3–6 most relevant experience files in full (not just the matched lines).
4. Write `evidence.md` in the application folder: a table of requirement → tags → best facts
   (by ref) → strength (✅/⚠️/❌), ordered by the track's priorities. Do this BEFORE drafting.
5. Ask the user about every ⚠️/❌ row that might have hidden evidence (max ~6 questions, most
   valuable first). Write answers back as new fact lines (`verified`, `src: user-YYYY-MM-DD`).
6. Run `python scripts/build_index.py` after any profile change (it also lints).

## Writing
- Follow `profile/style.md` strictly.
- CV: copy the track's base CV from `base/` (cv_variant in the track file), then select, reorder
  and rephrase bullets for the posting. One page. Respect the track's section order.
- Letter: `templates/coverletter.cls`, built around the posting's core needs with one piece of
  evidence each and an explicit link back.
- Build PDFs with `python scripts/build_pdf.py <file.tex>`; check the page count.

## Learning loop
- After any conversation where the user reveals new information, add it to the right experience
  file immediately, raise `depth` when warranted (stub → basic → deep), and rebuild the index.
- When the user gives feedback on a draft, fix the draft AND record the general rule in style.md.
- When the user edits a generated .tex, /sync compares it against the draft and records new facts
  in the profile and wording preferences in style.md.
- Update `tracker.md` when an application is created, sent, or gets a response;
  record outcomes in the application's `outcome.md`.

## Privacy
- Never copy national ID numbers, addresses or dates of birth from transcripts or contracts.
- Never read `.env` files in project repos.

## Commands (skills in .claude/skills/)
- `/apply <posting text or URL>`: full pipeline for one application.
- `/interview [topic]`: 10–15 min session deepening the profile (shallowest/most valuable first).
- `/sync <application folder>`: learn from the user's edits to a generated CV/letter.
- `/ingest <path>`: add a new source (repo, document, CV) to the profile.
- `/interview-prep [application folder]`: prepare for a job interview (essence of the role, ideas,
  what to know, likely questions with answer outlines from the profile) → `interview-prep.md`.
