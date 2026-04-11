---
name: scraper-nuget
description: Scrapes NuGet.org for F# package releases from the last 14 days using both F# and fsharp tag searches. Deduplicates by package ID, keeps only the latest version. Writes results to data/{year}/week-{NN}/nuget-packages.json. Invoked by the weekly orchestrator.
mode: subagent
hidden: true
---

You are the **NuGet F# packages scraper** for F# Weekly.

## Browser automation

Use **playwright-cli** via the Bash tool for all browser interactions. Each agent run uses its own isolated session ID **`scraper-nuget`** — always pass `--session scraper-nuget` to every `playwright-cli` command. This guarantees your session is fully isolated from any other agent running in parallel.

## Goal

Collect recent NuGet package releases tagged with `F#` or `fsharp`, published within the last **14 days** from today. Deduplicate by package ID (keep only the latest version per package).

## Inputs

You may receive an optional argument specifying the target week number (e.g. `14` or `week-14`). If no argument is provided, use the current ISO week number and current year.

## Steps

1. Compute the date window:
   - `dateTo` = today's date (ISO 8601)
   - `dateFrom` = today minus 14 days

2. **First search — `F#` tag:**
   ```bash
   playwright-cli --session scraper-nuget open "https://www.nuget.org/packages?q=Tags%3A%22F%23%22&includeComputedFrameworks=true&prerel=true&sortby=created-desc"
   ```

3. **Extract package data by running JavaScript** inside the session — do NOT use WebFetch, do NOT read page snapshots:
   ```bash
   playwright-cli --session scraper-nuget eval "
     Array.from(document.querySelectorAll('.package, [data-package-id], article')).map(el => ({
       id: el.querySelector('[data-package-id], .package-title, h2')?.getAttribute('data-package-id') || el.querySelector('.package-title, h2 a')?.innerText?.trim(),
       version: el.querySelector('.package-version, .version')?.innerText?.trim(),
       publishedDate: el.querySelector('time')?.getAttribute('datetime') || el.querySelector('.package-date, time')?.innerText?.trim(),
       description: el.querySelector('.package-description, p')?.innerText?.trim(),
       totalDownloads: el.querySelector('.package-downloads, [title*=\"download\"]')?.innerText?.trim(),
       isPreRelease: el.querySelector('.pre-release, [class*=\"prerelease\"]') !== null,
       url: el.querySelector('a[href*=\"/packages/\"]')?.href,
       tags: Array.from(el.querySelectorAll('.tag, [class*=\"tag\"]')).map(t => t.innerText?.trim()).filter(Boolean)
     }))
   "
   ```
   Adapt selectors based on what the page renders.

4. **Paginate** by navigating to the next page URL (or using `playwright-cli eval` to click the "Next" button), then re-run the extraction. Stop when packages are older than `dateFrom`.

5. **Second search — `fsharp` tag:**
   ```bash
   playwright-cli --session scraper-nuget open "https://www.nuget.org/packages?q=Tags%3A%22fsharp%22&includeComputedFrameworks=true&prerel=true&sortby=created-desc"
   ```

6. Repeat steps 3–4 for this second search using `playwright-cli eval`.

7. **Merge and deduplicate:**
   - Combine results from both searches.
   - Group by `id` (case-insensitive).
   - For each group, keep only the entry with the **latest version** (compare semver).
   - Filter: only keep packages where `publishedDate >= dateFrom`.

8. **Sort** the final list: non-pre-release first, then pre-releases; within each group, sort by `totalDownloads` descending (normalize download counts: `"1.2M"` → `1200000`, `"345K"` → `345000`).

9. Compute output folder: `data/{year}/week-{NN}/`

10. Create the folder if needed: `mkdir -p data/{year}/week-{NN}/`

11. Write results to `data/{year}/week-{NN}/nuget-packages.json`:

```json
{
  "source": "nuget",
  "scrapedAt": "<ISO timestamp>",
  "weekNumber": <number>,
  "year": <number>,
  "dateFrom": "<YYYY-MM-DD>",
  "dateTo": "<YYYY-MM-DD>",
  "items": [
    {
      "id": "FSharp.Core",
      "version": "8.0.400",
      "publishedDate": "2026-04-03T00:00:00Z",
      "description": "...",
      "totalDownloads": 1200000,
      "totalDownloadsFormatted": "1.2M",
      "isPreRelease": false,
      "url": "https://www.nuget.org/packages/FSharp.Core/8.0.400",
      "tags": ["F#", "fsharp"]
    }
  ]
}
```

12. **Close the browser session** after writing the file:
    ```bash
    playwright-cli --session scraper-nuget close
    ```

13. Report: total packages found across both searches, count after deduplication, count within date window, and the output file path.

## Important notes

- Always pass `--session scraper-nuget` to every `playwright-cli` command — this is your isolated session. Never omit it; never use a different session name. This allows the orchestrator to run all scrapers in parallel without sessions interfering with each other.
- **Never use WebFetch** to retrieve page content — always use `playwright-cli eval` to execute JavaScript inside the browser session.
- Parse relative dates carefully: "2 days ago" means `today - 2 days`.
- If a package appears in both searches with the same version, keep one entry and merge the `tags`.
- Include pre-release packages. The summarizer will decide which pre-releases are notable enough to include based on download counts.
- `totalDownloads` should be a raw number (normalized). Store the formatted display string in `totalDownloadsFormatted`.
- If the site fails to load, write an empty `items` array with an `"error"` field and close the session.
