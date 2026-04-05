---
description: Run the full F# Weekly pipeline — scrape all sources in parallel, then generate the newsletter draft. Usage: /weekly [week-number]. Example: /weekly 14 or /weekly 2026-14. Omit the argument to use the current week.
agent: weekly-orchestrator
subtask: true
---

Run the full F# Weekly data collection and newsletter generation pipeline for week $ARGUMENTS.

If no week number was provided in $ARGUMENTS, use the current ISO week number and current year.

Steps:
1. Launch all 7 scrapers in parallel (Microsoft DevBlogs, Twitter, Bluesky, Mastodon, NuGet, GitHub, YouTube)
2. Wait for all scrapers to complete
3. Run the summarizer to generate the newsletter draft

Output will be written to data/{year}/week-{NN}/:
- microsoft-posts.json
- twitter.json
- bluesky.json
- mastodon.json
- nuget-packages.json
- github-repos.json
- youtube-videos.json
- newsletter-draft.html  ← WordPress-ready
- newsletter-draft.md    ← human-readable preview
