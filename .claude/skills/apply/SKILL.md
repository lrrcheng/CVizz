---
name: apply
description: Create a tailored CV and cover letter for one job posting, using the verified profile. Use when the user pastes a job posting or link, or asks to apply for a position.
---

# /apply: one application, end to end

Input: posting text, a URL, or a file. If nothing is given, ask for the posting.

## Steps
1. **Save the posting.** Create `applications/<YYYY-MM>-<company>-<role-slug>/posting.md` with
   frontmatter (`company`, `role`, `location`, `deadline`, `url`, `language`, `track`) and the
   full posting text verbatim. If given a URL, fetch it (FINN, LinkedIn and NAV links:
   `python scripts/find_jobs.py --show <url>`); if fetching fails, ask the user to paste it.
2. **Pick the track** (engineering / quant / asset-management) from the role, using each track
   file's target-role list. State the choice in one line; the user can override.
3. **Retrieve evidence** following the procedure in CLAUDE.md (index → `--find` per requirement
   → read top experience files in full). Also read `tracks/<track>.md` and `profile/motivation.md`.
   Check `companies/<company>.md` if it exists, and earlier letters to the same company (archive
   folders listed in `profile/sources.md`); don't repeat a weak angle that didn't work.
   If the track file has a "Letter: company hook" section, also find one recent, role-relevant fact
   about the company (latest quarterly or annual report, news from the last six months): reuse
   `companies/<company>.md` or search, and save it there with its source.
4. **Write `evidence.md`**: requirement → tags → best fact refs → ✅/⚠️/❌, plus a short
   "angle" paragraph: the 2–3 stories the letter will be built on and why.
5. **Ask questions** for ⚠️/❌ rows where the user might have unrecorded evidence, plus anything
   the letter needs that only the user knows (e.g. why this company). Use AskUserQuestion or plain
   text; at most ~6 questions, most valuable first. For each skill/tool the posting asks for, apply
   the rules in style.md "Skills the posting asks for": touched → list as "(basic)"; never touched but
   clearly wanted → ask whether the user wants to do a small project before sending (suggest one that
   fits their existing projects, and note the deadline). Save Q&A in `questions.md`. Write every new
   fact back into `profile/` and run `python scripts/build_index.py`.
6. **Draft the CV**: copy `base/cv-<variant>.tex` → `cv.tex`; select, reorder and rephrase
   bullets for this posting; every bullet keeps its `% src:` comment. One page.
7. **Draft the letter**: `cover-letter.tex` with `\documentclass{coverletter}`, following
   `profile/style.md` (requirement → evidence paragraphs). Only facts with status verified or stated.
   If the track allows a company hook and a fact clearly fits, add one light sentence to the opening
   (style.md "Company hook"). Otherwise leave it out.
8. **Build both PDFs**: `python scripts/build_pdf.py <folder>/cv.tex <folder>/cover-letter.tex`.
   Fix overflow until each is exactly one page.
9. **Self-check before handing over**: re-read the letter against `evidence.md`. Every claim must
   map to a fact ref, numbers must match exactly, no style.md "avoid" patterns, no typos.
   No em-dashes and (almost) no semicolons in the letter body. Read each paragraph and ask: does every
   sentence connect clearly to the posting? If a sentence only adds information, cut it.
10. **Snapshot the drafts** as `cv.draft.tex` and `cover-letter.draft.tex` (used by /sync later),
    add a row to `tracker.md` (status: drafted), set the posting's status to `applied` in
    `jobs/shortlist.md` if it's there, and report: track, angle, any facts that are
    `stated` but central (ask the user to confirm), and the PDF paths.
