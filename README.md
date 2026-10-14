# Job application system for Claude Code

Write tailored, accurate CVs and cover letters with [Claude Code](https://claude.com/claude-code).
Your experience is stored once as a growing, verified **profile**. Every application selects and
phrases from it, asks you about gaps, and writes your answers back, so the profile gets more
complete with each application.

- **No invented facts.** Every claim in a CV or letter traces back to a fact in your profile.
  When something is missing, Claude asks instead of stretching.
- **LaTeX output.** One-page CVs and letters. All layout lives in `templates/`, so the content files
  stay easy to edit by hand.
- **Learns your style.** Feedback and your own edits become writing rules in `profile/style.md`.
- **Career tracks.** Engineering, quant and asset management come pre-configured; add your own.
- **Private by default.** Your profile, CVs and applications are gitignored. Only the framework is shared.
  A `.ignore` file keeps these private folders searchable for Claude Code (its search tools skip
  gitignored files otherwise).

## Setup

1. **Install the tools**
   - [Claude Code](https://claude.com/claude-code) (CLI or the VS Code extension)
   - Python 3.10+, then: `pip install -r requirements.txt`
   - A LaTeX distribution with `latexmk`:
     - Windows: [MiKTeX](https://miktex.org/) + [Strawberry Perl](https://strawberryperl.com/) (latexmk needs Perl).
       In the MiKTeX console, allow packages to be installed automatically.
     - macOS: [MacTeX](https://www.tug.org/mactex/) · Linux: `texlive-full` or `texlive-latex-extra` + `latexmk`
   - Optional: the VS Code extension **LaTeX Workshop** for a live PDF preview on save (settings are included).
2. **Create your personal files**
   ```
   python scripts/init.py
   ```
   It asks for your name and contact details and creates `profile/`, `tracks/`, `base/`, `TODO.md`
   and the other personal files from `scaffold/`. It never overwrites existing files.
3. **Feed it your material.** Put your CV(s), transcript and earlier cover letters in `inbox/`, open
   the folder in Claude Code and run `/ingest inbox/`. Also give it paths to code projects worth showing.
4. Follow `TODO.md`.

## Commands

| Command | What it does |
|---|---|
| `/apply <job posting text or URL>` | Saves the posting, maps its requirements to your facts, asks about gaps, drafts a CV and cover letter, and builds the PDFs |
| `/interview [topic]` | A 10–15 minute Q&A that fills holes in your profile (e.g. `/interview why this field`) |
| `/sync [application folder]` | After you edit a generated `.tex`, records new facts and your wording preferences |
| `/ingest <path>` | Adds a CV, transcript, document or code repository to your profile |
| `/interview-prep [application folder]` | Prepares you for a job interview: what the role really is, ideas to think about, what to know to impress, and the questions to be ready for, with answer outlines from your own facts |

## Folder structure

```
SHARED (in git)
  CLAUDE.md               Rules Claude follows in this folder
  .claude/skills/         The commands above
  scripts/                init.py, build_index.py (indexes, lint, search), build_pdf.py
  templates/              cv.cls and coverletter.cls: all LaTeX layout
  scaffold/               Starter versions of every personal file (used by init.py)

PERSONAL (gitignored, created by init.py)
  profile/experiences/    One file per job, project, education or award group: your facts
  profile/skills.md       Allowed skill tags, with synonyms
  profile/about-me.md     Contact info, languages, interests
  profile/motivation.md   Goals and "why this field", in your own words
  profile/style.md        Writing rules (good defaults included)
  profile/sources.md      Where every fact came from
  tracks/                 What each career track looks for, and how to frame your experience
  base/                   Master CVs per track and an example letter
  applications/           One folder per application (posting, evidence, questions, CV, letter)
  companies/              Notes on companies, reused across applications
  generated/              Indexes, skill matrix, gap reports, open questions (don't edit)
  inbox/                  Drop new material here, then /ingest it
  tracker.md, TODO.md     Application overview and open tasks
  personal/               Your own resources: diplomas, transcripts, references, old CVs (any subfolders)
```

## How facts work

Each fact is one line in an experience file:

```
- F3 [python, data-analysis] Analysed sensor data from 12 test runs and found the cause of a drift · stated · src: CV-2025
```

- **Tags** come only from `profile/skills.md`, so one tag search finds everything relevant.
- **Status:** `verified` (confirmed by you or a document), `stated` (from your own CV/letters),
  `unverified` (inconsistent; never used until you confirm it).
- **Source** points to an entry in `profile/sources.md`.

Each bullet in a generated `.tex` ends with a hidden `% src: entry#F3` comment, so you can always
see where a claim came from.

## Useful commands

```
python scripts/build_index.py                       # rebuild generated/ and lint the profile
python scripts/build_index.py --find "SQL" "PLC"     # which facts match a phrase from a posting?
python scripts/build_pdf.py applications/<folder>/cv.tex
```

`generated/GAPS-<track>.md` shows which skills a track expects that your profile can't prove yet:
useful for deciding what to learn or build next.

## Typical workflow

1. Find a posting → `/apply` with the text or link.
2. Answer Claude's questions about gaps. Answers are saved to your profile.
3. Review `evidence.md`, the CV and the letter in the application folder. Give feedback or edit the `.tex`.
4. `/sync` so Claude learns from your edits.
5. Send it, update `tracker.md`, and record the outcome in `outcome.md`.
6. Invited to an interview? `/interview-prep` with the application folder, then ask for a mock interview.
7. When you have spare time, `/interview` to deepen the profile.

## Keeping your data private

If you fork or push your copy, check what git would publish before every push:

```
git status --short          # should list only framework files
git ls-files                # everything already committed
```

Your profile, CVs, letters and documents must never appear in either list. If you keep personal
material in a new folder, add it to both `.gitignore` (so git skips it) and `.ignore` (so Claude
can still search it).

## License

MIT. See `LICENSE`.
