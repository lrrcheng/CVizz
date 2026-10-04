---
name: interview
description: Run a short interview session that deepens the user's experience profile, answering open questions and building STAR stories. Use when the user wants to improve their profile, has some spare time, or asks to be interviewed about an experience or their motivation.
---

# /interview: deepen the profile

Optional argument: a topic (an experience id, a track like "quant", or "why this field").

## Steps
1. Run `python scripts/build_index.py` and read `generated/OPEN-QUESTIONS.md`, `generated/INDEX.md`
   and, if a track is given, `generated/GAPS-<track>.md`.
2. Choose the focus (if no topic is given), in this priority:
   a. `unverified` facts and contradictions between sources (these block drafting);
   b. gaps in required tags of tracks the user is actively applying to;
   c. the most valuable experience still at `stub` depth;
   d. the "why this field" story in motivation.md (e.g. for a career switch), if still unbuilt.
   Say in one line what you'll cover and why.
3. Ask ONE question at a time, conversationally. Follow up on vague answers to get specifics:
   numbers, their personal role vs the team's, decisions and trade-offs, what went wrong, results.
   Aim for about 8–12 questions (10–15 minutes) unless the user wants to continue.
4. After every few answers, write them into the profile immediately:
   - new fact lines (`verified`, `src: user-YYYY-MM-DD`) with tags from skills.md;
   - fix or delete contradicted facts; remove answered open questions;
   - fill the `## Story (STAR)` section when there's enough material;
   - raise `depth` (stub → basic → deep) when the entry has context, role, actions, results and a story.
   Motivation answers go to `profile/motivation.md` in the user's own words.
5. End by running `python scripts/build_index.py` and summarising: facts added, depth changes,
   and how track gap coverage changed (e.g. "quant: 8/12 → 10/12 strong").
