---
name: weekly-collect
description: Collects F# Weekly source data. Use when running /weekly, retrying a failed source, or diagnosing newsletter collection.
---

# Weekly Collect

Run from the repository root:

```bash
python3 .agents/skills/weekly-collect/scripts/collect.py --week "$ARGUMENTS"
```

Omit `--week` when no argument was supplied. Accepted values: `38`, `week-38`, `2026-38`, `2026/38`.

With no `--source`, the command collects every source required for the newsletter: Microsoft DevBlogs, published issues, NuGet, GitHub, Mastodon, YouTube, Bluesky, and X/Twitter. Always use this all-source command for a new weekly run; use `--source` only to retry or diagnose one source. Do not prepare or render a newsletter until the manifest contains an entry for every source and no source is `failed` or `partial`.

Useful options:

```bash
python3 .agents/skills/weekly-collect/scripts/collect.py --source nuget
python3 .agents/skills/weekly-collect/scripts/collect.py --dry-run
```

The command writes source JSON and `manifest.json` under `data/{year}/week-{NN}/`. Exit code 0 means collection completed; individual sources may still be `blocked` or `partial` in the manifest. `--dry-run` is diagnostic and overwrites its target, so use `FSHARP_WEEKLY_DATA_DIR=/tmp/fsharp-weekly` when testing an existing week.

If the report says login is required, ask the user whether to run one of these commands. Never enter credentials for them. The login browser must be closed after the user finishes logging in before rerunning collection, otherwise the persistent profile may be reported as already in use:

```bash
python3 .agents/skills/weekly-collect/scripts/login.py bluesky
python3 .agents/skills/weekly-collect/scripts/login.py twitter
```

After the user completes login, rerun only that source with `--source bluesky` or `--source twitter`.
