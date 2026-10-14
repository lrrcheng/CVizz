---
name: interview-prep
description: Prepare the user for a job interview for one application. Explains what the role really is, sparks ideas linking the role to the user's skills, lists what to know to impress, and the questions to be ready for, with answer outlines built only from the profile. Use when the user has an interview coming up, asks how to prepare for one, or asks what they might be asked about an application.
---

# /interview-prep: get ready for one interview

Argument: an application folder (default: the most recently modified one in `applications/`),
optionally followed by notes from the invitation (date, format, interviewers, language).
Output: `applications/<folder>/interview-prep.md`. Not to be confused with `/interview`,
which deepens the profile.

## Steps
1. **Read the application.** In the folder: `posting.md`, `evidence.md`, `questions.md`, the
   current `cv.tex` and `cover-letter.tex` (what was sent, not the `.draft.tex`), and `outcome.md`
   if it exists. Then `companies/<company>.md`, `tracks/<track>.md`, `profile/motivation.md`,
   `profile/about-me.md`, and **every experience file cited** in the `% src:` comments of the CV
   and letter, in full (facts, `## Story (STAR)`, open questions).
2. **Ask only what changes the prep**, in one message, if not already known: interview date,
   format (HR screen, technical, case, panel), language, interviewer roles. If the user doesn't
   know yet, assume a 30–45 minute first interview with a manager from the team and say so.
3. **Research the company and the domain** (WebSearch/WebFetch): the unit's own pages, the latest
   annual or quarterly report, news from the last 12 months, and the market or technology the
   team works with. Every company-specific claim gets a source URL and the date it was checked.
   If web tools are unavailable, mark company-specific claims "(check)". Never present an
   inference as a fact: write "most likely" when you are reasoning from the posting.
4. **Write `interview-prep.md`** with these sections, in this order:
   1. **The essence of the role.** One or two short paragraphs in plain words: the problem the
      team exists to solve, how that creates value for the company, what an intern most likely
      does day to day, and what a good summer delivers. Keep what the posting says apart from
      what is inferred.
   2. **Thinking about the role.** A paragraph or two written to the user, meant to make them
      reflect and come up with ideas: where the work connects to things they have done and liked
      (cite fact refs), where their background gives a fresh angle, and directions they have never
      touched but might find interesting. End with 3–5 concrete ideas or open questions they could
      think about or raise ("If I joined, I'd want to try…"). Ideas outside the profile are welcome
      here, framed as ideas and never as experience.
   3. **What to know to impress.** (a) A short primer: 6–10 core concepts and terms of the domain,
      each explained in a sentence or two. (b) The company: key numbers, strategy and recent
      events relevant to the team, with sources. (c) What is happening in this market right now,
      dated. (d) Tools and methods the team likely uses, and the one or two worth brushing up on
      first. (e) 2–3 talking points that are impressive but honest: a link between a recorded fact
      and the company's real situation.
   4. **Questions to be ready for**, most likely first, grouped:
      - *Opening and motivation*: tell me about yourself, why this company and team, why this
        field, what next. Give an answer outline in bullets from fact refs and motivation.md (the
        user's own words), not a script.
      - *Deep-dives on the CV and letter*: every claim an interviewer may probe (each number,
        each "built", each title), the likely follow-ups ("how did you measure that?", "what was
        your part and what was the team's?"), and what to have ready. Flag every claim whose fact
        is `stated` or has open questions: the user must be able to defend it, or it should come
        out of the CV.
      - *Role and technical*: concepts, small cases, estimation or a coding/SQL task the posting
        makes likely, each with a hint on how to approach it. Full solutions only when short.
      - *Behavioural (STAR)*: teamwork, conflict, failure, a decision under uncertainty, learning
        something fast, taking the lead. Map each to the best story in the profile (entry and refs).
        If no story fits, say so.
      - *Gaps and awkward questions*: every ⚠️/❌ row in `evidence.md`, date gaps, contradictions,
        and skills the posting names that the user lacks. Give an honest framing (the closest real
        evidence and how they would close the gap), never a stretch.
   5. **Questions to ask them.** 4–6 specific questions that show understanding of the role and
      can't be answered from the website.
   6. **Before the interview.** A checklist: facts to verify, numbers to know exactly as they
      appear on the CV, stories to rehearse aloud, documents and logistics.

## Rules
- **No invented facts about the user.** Answer outlines use only `verified` or `stated` facts,
  cited by ref, never `unverified` ones. Where a good answer needs something the profile doesn't
  have, write `[fill in: …]` and add the question to that experience file's open questions
  (and to `TODO.md` if the interview is close).
- Write in English and follow the plain-language rules in `profile/style.md` (no em-dashes, short
  sentences). If the interview is in another language, also give the key terms and the
  "tell me about yourself" outline in that language.
- Readable in 20–30 minutes: prioritise and cut. Don't repeat the cover letter. The interview is
  where the stories get depth.

## Finish
- Save new company research in `companies/<company>.md` (dated, with sources) so later
  applications reuse it. Set the tracker status to `interview` if an interview is scheduled.
- Report: the file path, the three most likely questions, and the claims that are riskiest to
  defend.
- Offer a mock interview: one question at a time, short feedback on content, structure and
  length after each answer. Write any new facts the user reveals into the profile (as `/interview`
  does) and run `python scripts/build_index.py`.
