---
name: ingest
description: Add a new source (code repository, project folder, CV, transcript, reference letter, report) to the user's experience profile. Use when the user gives a path to a project or document, or says they have a new CV, grade or project.
---

# /ingest: add a source to the profile

Argument: one or more paths (or a description; then locate it in the user's code or document folders).

## Steps
1. Check `profile/sources.md`: is it already ingested? For repos, compare the latest commit date
   with the "Ingested" date and only process what's new.
2. Read the source:
   - **Repo/project:** README and docs, dependency files (requirements.txt, package.json,
     CMakeLists), the main source files' structure, and `git log --author` (try the name and email
     from `profile/about-me.md`) for dates, commit count and which parts the user wrote. Never read `.env`.
   - **Documents:** extract text (`pdftotext -layout`, python-docx). For scanned PDFs, extract
     page images with pypdf + PIL and view them.
3. Write facts into the right experience file (or create a new one with full frontmatter; check
   that the id matches the filename). Status: `verified` for what the source proves (git authorship,
   official documents), `stated` for the user's own descriptions. Tag only from `profile/skills.md`.
4. Add what the source can't tell (the user's role, decisions, results, motivation) as
   `## Open questions` in the entry.
5. Register the source in `profile/sources.md` with today's date (and commit hash for repos).
6. Never copy personal ID numbers, addresses or birth dates.
7. Run `python scripts/build_index.py`, fix any warnings, and summarise: facts added, entries
   touched, new open questions, and changes in track gap coverage.
