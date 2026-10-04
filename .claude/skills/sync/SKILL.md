---
name: sync
description: Learn from the user's manual edits to a generated CV or cover letter. Records new or corrected facts in the profile and wording preferences in style.md. Use when the user says they have edited a draft, or asks to sync an application.
---

# /sync: learn from edits

Argument: an application folder (default: the most recently modified one in `applications/`).

## Steps
1. For each of `cv.tex` and `cover-letter.tex` in the folder, diff against its `*.draft.tex`
   snapshot (`git diff --no-index --word-diff <draft> <current>` works without a repo).
2. Classify each change:
   - **Fact change** (new claim, corrected number/date/title, removed claim): update or add the
     fact in `profile/experiences/` (`verified`, `src: user-YYYY-MM-DD`). If the user removed a claim,
     ask whether it's wrong (then fix or delete the fact) or just not wanted here.
   - **Wording/style change** (word choice, tone, structure, length): if it reflects a general
     preference, add a concise rule to `profile/style.md` under "Wording preferences" or "Avoid".
     Don't record one-off, posting-specific tweaks.
   - **Layout change**: if it should apply everywhere, propose a change to `templates/*.cls`
     or the `base/` CV and ask before editing.
3. Ask about anything ambiguous instead of guessing.
4. Replace the `*.draft.tex` snapshots with the current files, so the next /sync only sees new edits.
5. Run `python scripts/build_index.py` and summarise what was learned.
