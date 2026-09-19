# Collection Sources

| Source | Method |
|---|---|
| Microsoft | .NET Blog RSS |
| Published issues | F# Weekly category RSS, latest three full entries |
| NuGet | V3 search and registration APIs |
| GitHub | Authenticated `gh api` repository search and release endpoints |
| Mastodon | Public Hachyderm hashtag timeline API |
| YouTube | Official .NET Atom feed plus bounded public browser search |
| Bluesky | Persistent authenticated browser session |
| Twitter | Persistent authenticated browser session |

All sources use the same rolling 14-day window computed by `collect.py`. The week identifies the output folder; it does not change the date window.

Browser profiles are stored under `.playwright-cli/weekly-profiles/`, which is ignored by git. Browser sources are optional and must never prevent API/RSS sources from completing.
