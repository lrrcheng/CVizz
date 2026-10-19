---
# Saved searches for /find-jobs (scripts/find_jobs.py). Edit freely; Claude suggests changes after each run.
max_age_days: 45          # ignore postings published longer ago than this
exclude_title: [senior, erfaren, principal, head of, director, direktør, leder, sykepleier, lege, lærling]
searches:                 # sources: finn, linkedin, nav (default: all three); location: LinkedIn only (default Norway)
  - {query: sommerjobb ingeniør, track: engineering, sources: [finn, nav]}
  - {query: summer internship engineering, track: engineering, sources: [linkedin]}
  - {query: sommerjobb finans, track: asset-management, sources: [finn, nav]}
  - {query: summer internship trading, track: quant, sources: [linkedin]}
  - {query: summer internship, sources: [finn]}
---

# Job searches

The searches `/find-jobs` runs. Each one is a query plus the track it's for (the track only helps Claude
sort the results; it doesn't filter anything).

- **FINN and NAV** (arbeidsplassen.no) search the full ad text, and every word must match. Norwegian
  works best: `sommerjobb kybernetikk` finds summer jobs that mention cybernetics anywhere in the ad.
  NAV also carries most FINN ads, plus ads that are only on NAV.
- **LinkedIn** works best in English (`summer internship trading`). It rate-limits quickly, so keep it
  to about six searches. `location` is a country or LinkedIn's full name for a city
  (`Norway`, `Sweden`, `"Amsterdam, North Holland, Netherlands"`): a bare city name returns nothing.
- **Indeed** isn't supported: it blocks automated requests. Most Norwegian Indeed ads also appear on
  FINN, NAV or the company's own site.
- `exclude_title` drops postings whose title contains any of these words (case doesn't matter, and
  `leder` also catches `prosjektleder`).
