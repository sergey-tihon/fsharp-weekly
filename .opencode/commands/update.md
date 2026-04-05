---
description: Re-generate the newsletter draft from already-scraped data. Usage: /update [week-number]. Example: /update 14 or /update 2026-14. Omit the argument to use the current week. Requires /weekly to have been run first.
agent: summarizer
subtask: true
---

Generate (or re-generate) the F# Weekly newsletter draft from already-scraped data for week $ARGUMENTS.

If no week number was provided in $ARGUMENTS, use the current ISO week number and current year.

Read the scraped JSON files from data/{year}/week-{NN}/, fetch the last published F# Weekly from sergeytihon.com to deduplicate, and produce:
- data/{year}/week-{NN}/newsletter-draft.html  ← WordPress block HTML, ready to paste
- data/{year}/week-{NN}/newsletter-draft.md    ← Markdown preview

If no scraped data exists for the specified week, report an error and suggest running /weekly first.

This command is useful when:
- You want to re-summarize after manually editing the scraped JSON files
- The summarizer failed during /weekly but the scrapers succeeded
- You want to regenerate with a different editorial focus
