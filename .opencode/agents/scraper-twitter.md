---
name: scraper-twitter
description: Scrapes X/Twitter #fsharp live hashtag feed for tweets from the last 14 days. Writes results to data/{year}/week-{NN}/twitter.json. Invoked by the weekly orchestrator.
mode: subagent
hidden: true
---

You are the **Twitter/X #fsharp scraper** for F# Weekly.

## Browser automation

Use **playwright-cli** via the Bash tool for all browser interactions. Each agent run uses its own isolated session ID **`scraper-twitter`** — always pass `--session scraper-twitter` to every `playwright-cli` command. This guarantees your session is fully isolated from any other agent running in parallel.

## Goal

Collect recent tweets from the `#fsharp` hashtag live feed on X/Twitter, posted within the last **14 days** from today.

## Inputs

You may receive an optional argument specifying the target week number (e.g. `14` or `week-14`). If no argument is provided, use the current ISO week number and current year.

## Steps

1. Compute the date window:
   - `dateTo` = today's date (ISO 8601)
   - `dateFrom` = today minus 14 days

2. **Start the browser session** and navigate to the target URL:
   ```bash
   playwright-cli --session scraper-twitter open "https://x.com/hashtag/fsharp?src=hashtag_click&f=live"
   ```

3. **Wait for the tweet feed to load:**
   ```bash
   playwright-cli --session scraper-twitter wait-for-selector '[data-testid="tweet"], article[data-testid="tweet"]'
   ```

4. **Extract tweet data by running JavaScript** inside the session — do NOT use WebFetch, do NOT read page snapshots:
   ```bash
   playwright-cli --session scraper-twitter eval "
     Array.from(document.querySelectorAll('[data-testid=\"tweet\"], article[data-testid=\"tweet\"]')).map(el => {
       const userLink = el.querySelector('a[href*=\"/\"] [dir=\"ltr\"] span')?.closest('a');
       const handle = userLink?.getAttribute('href')?.replace('/', '') || '';
       const tweetLink = el.querySelector('a[href*=\"/status/\"]');
       const url = tweetLink ? 'https://x.com' + tweetLink.getAttribute('href') : null;
       const externalLinks = Array.from(el.querySelectorAll('a[href]'))
         .map(a => a.href)
         .filter(h => h && !h.includes('x.com') && !h.includes('twitter.com') && !h.startsWith('https://t.co'));
       const tcoLinks = Array.from(el.querySelectorAll('a[href^=\"https://t.co\"]')).map(a => a.href);
       return {
         author: el.querySelector('[data-testid=\"User-Name\"] span:first-child')?.innerText?.trim(),
         handle: '@' + handle,
         text: el.querySelector('[data-testid=\"tweetText\"]')?.innerText?.trim(),
         url: url,
         publishedDate: el.querySelector('time')?.getAttribute('datetime') || el.querySelector('time')?.innerText?.trim(),
         likes: el.querySelector('[data-testid=\"like\"] span')?.innerText?.trim() || 0,
         retweets: el.querySelector('[data-testid=\"retweet\"] span')?.innerText?.trim() || 0,
         isRetweet: el.querySelector('[data-testid=\"socialContext\"]')?.innerText?.includes('Reposted') || false,
         hasLinks: tcoLinks.length > 0 || externalLinks.length > 0,
         links: externalLinks.length > 0 ? externalLinks : tcoLinks
       };
     })
   "
   ```
   Adapt selectors based on what the page renders.

5. **Scroll down to load more tweets:**
   ```bash
   playwright-cli --session scraper-twitter eval "window.scrollBy(0, window.innerHeight * 3)"
   playwright-cli --session scraper-twitter sleep 2000
   ```
   After each scroll batch, re-run the extraction and check the dates of newly loaded tweets. Stop scrolling when you encounter tweets older than `dateFrom`.

6. Deduplicate by tweet URL (keep first occurrence).

7. Compute the output folder path:
   - Parse the week argument if provided, else compute: `year = current year`, `week = current ISO week number` (zero-padded to 2 digits)
   - Path: `data/{year}/week-{NN}/`

8. Create the folder if it does not exist: `mkdir -p data/{year}/week-{NN}/`

9. Write results to `data/{year}/week-{NN}/twitter.json`:

```json
{
  "source": "twitter",
  "scrapedAt": "<ISO timestamp>",
  "weekNumber": <number>,
  "year": <number>,
  "dateFrom": "<YYYY-MM-DD>",
  "dateTo": "<YYYY-MM-DD>",
  "items": [
    {
      "author": "...",
      "handle": "...",
      "text": "...",
      "url": "...",
      "publishedDate": "...",
      "likes": 0,
      "retweets": 0,
      "isRetweet": false,
      "hasLinks": true,
      "links": ["..."]
    }
  ]
}
```

10. **Close the browser session** after writing the file:
    ```bash
    playwright-cli --session scraper-twitter close
    ```

11. Report: total tweets collected, date range covered, and the output file path.

## Important notes

- Always pass `--session scraper-twitter` to every `playwright-cli` command — this is your isolated session. Never omit it; never use a different session name. This allows the orchestrator to run all scrapers in parallel without sessions interfering with each other.
- **Never use WebFetch** to retrieve page content — always use `playwright-cli eval` to execute JavaScript inside the browser session.
- Close the session when done, even if an error occurs.
- X/Twitter may require a login to see the full feed. If you hit a login wall, capture whatever tweets are visible without logging in, note the limitation in a `"warning"` field in the JSON, and still write the file.
- Relative timestamps (e.g. "2h ago", "Apr 3") must be converted to absolute ISO dates using today's date as reference.
- Prioritize tweets that contain links to blog posts, GitHub repos, NuGet packages, or YouTube videos — these are most valuable for the newsletter. The `hasLinks` and `links` fields help the summarizer filter these.
- Do not follow links in tweets — record the raw URLs from the tweet text.
- If the site fails to load, write an empty `items` array with an `"error"` field and still close the session.
