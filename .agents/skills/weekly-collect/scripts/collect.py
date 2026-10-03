from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import shutil
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

from common import ROOT, RunContext, envelope, in_window, iso_now, parse_cli_json, parse_date, request_bytes, request_json, resolve_context, run, write_json


MICROSOFT_FEED = "https://devblogs.microsoft.com/dotnet/feed/"
PUBLISHED_FEED = "https://sergeytihon.com/category/f-weekly/feed/"
NUGET_SEARCH = "https://azuresearch-usnc.nuget.org/query"
MASTODON_API = "https://hachyderm.io/api/v1/timelines/tag/fsharp"
YOUTUBE_DOTNET_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=UCvtT19MZW8dq5Wwfu6B0oxw"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.links.append({"url": self._href, "text": " ".join("".join(self._text).split())})
            self._href = None
            self._text = []


def format_downloads(value: int) -> str:
    return f"{value:,}"


def strip_html(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def collect_microsoft(context: RunContext) -> dict[str, Any]:
    body, _ = request_bytes(MICROSOFT_FEED)
    root = ET.fromstring(body)
    items = []
    for entry in root.findall("./channel/item"):
        published = entry.findtext("pubDate")
        if not in_window(published, context):
            continue
        categories = [node.text or "" for node in entry.findall("category")]
        items.append(
            {
                "title": entry.findtext("title", "").strip(),
                "url": entry.findtext("link", "").strip(),
                "publishedDate": parse_date(published).isoformat().replace("+00:00", "Z"),
                "author": entry.findtext("{http://purl.org/dc/elements/1.1/}creator", "").strip(),
                "snippet": strip_html(entry.findtext("description", "")),
                "tags": categories,
            }
        )
        if context.dry_run:
            break
    return envelope(context, "microsoft-devblogs", items)


def collect_published(context: RunContext) -> dict[str, Any]:
    body, _ = request_bytes(PUBLISHED_FEED)
    root = ET.fromstring(body)
    issues = []
    all_urls: list[str] = []
    content_name = "{http://purl.org/rss/1.0/modules/content/}encoded"
    for entry in root.findall("./channel/item")[: 1 if context.dry_run else 3]:
        parser = LinkParser()
        parser.feed(entry.findtext(content_name, ""))
        links = [link for link in parser.links if link["url"].startswith(("http://", "https://"))]
        urls = list(dict.fromkeys(link["url"] for link in links))
        all_urls.extend(urls)
        published = parse_date(entry.findtext("pubDate"))
        issues.append(
            {
                "title": entry.findtext("title", "").strip(),
                "url": entry.findtext("link", "").strip(),
                "publishedDate": published.date().isoformat() if published else None,
                "urls": urls,
                "linkedItems": links,
            }
        )
    result = envelope(context, "fsharp-weekly-published", [])
    result.pop("items")
    result["issues"] = issues
    result["allUrls"] = list(dict.fromkeys(all_urls))
    return result


def parse_nuget_page(body: str) -> list[dict[str, Any]]:
    chunks = re.split(r'<li\s+class="package"[^>]*>', body, flags=re.IGNORECASE)[1:]
    items = []
    for chunk in chunks:
        package = re.search(r'data-package-id="([^"]+)"\s+data-package-version="([^"]+)"', chunk)
        published = re.search(r'data-datetime="([^"]+)"', chunk)
        if not package or not published:
            continue
        downloads_match = re.search(r'([\d,]+)\s+total downloads', chunk, re.IGNORECASE)
        description_match = re.search(r'<div class="package-details">(.*?)</div>', chunk, re.IGNORECASE | re.DOTALL)
        tags = [html.unescape(tag) for tag in re.findall(r'title="Search for [^"]+">([^<]+)</a>', chunk, re.IGNORECASE)]
        package_id, version = map(html.unescape, package.groups())
        downloads = int(downloads_match.group(1).replace(",", "")) if downloads_match else 0
        items.append(
            {
                "id": package_id,
                "version": version,
                "publishedDate": published.group(1),
                "description": strip_html(description_match.group(1)) if description_match else "",
                "totalDownloads": downloads,
                "totalDownloadsFormatted": format_downloads(downloads),
                "isPreRelease": "-" in version,
                "url": f"https://www.nuget.org/packages/{urllib.parse.quote(package_id)}/{urllib.parse.quote(version)}",
                "tags": tags,
            }
        )
    return items


def collect_nuget(context: RunContext) -> dict[str, Any]:
    found: dict[str, dict[str, Any]] = {}
    for query in ('Tags:"F#"', 'Tags:"fsharp"'):
        for page in range(1, 2 if context.dry_run else 21):
            url = "https://www.nuget.org/packages?" + urllib.parse.urlencode(
                {
                    "q": query,
                    "includeComputedFrameworks": "true",
                    "prerel": "true",
                    "sortby": "created-desc",
                    "page": page,
                }
            )
            body, _ = request_bytes(url)
            page_items = parse_nuget_page(body.decode("utf-8"))
            if not page_items:
                break
            reached_old = False
            for item in page_items:
                if in_window(item["publishedDate"], context):
                    found.setdefault(item["id"].lower(), item)
                elif parse_date(item["publishedDate"]).date() < context.date_from:
                    reached_old = True
            if reached_old:
                break
    items = list(found.values())
    items.sort(key=lambda item: (item["isPreRelease"], -item["totalDownloads"], item["id"].lower()))
    return envelope(context, "nuget", items)


def gh_json(arguments: list[str]) -> Any:
    result = run(["gh", "api", *arguments], timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def collect_github(context: RunContext) -> dict[str, Any]:
    if not shutil.which("gh"):
        raise RuntimeError("gh is not installed")
    query = f"topic:fsharp pushed:>={context.date_from.isoformat()}"
    page_size = 5 if context.dry_run else 100
    payload = gh_json(["search/repositories", "-X", "GET", "-f", f"q={query}", "-f", "sort=updated", "-f", "order=desc", "-f", f"per_page={page_size}"])

    def enrich(repo: dict[str, Any]) -> dict[str, Any]:
        release = None
        try:
            latest = gh_json([f"repos/{repo['full_name']}/releases/latest"])
            if in_window(latest.get("published_at"), context):
                release = {"tag": latest.get("tag_name"), "releaseUrl": latest.get("html_url"), "publishedDate": latest.get("published_at")}
        except RuntimeError:
            pass
        return {
            "name": repo["full_name"],
            "url": repo["html_url"],
            "description": repo.get("description") or "",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language"),
            "lastUpdated": repo.get("pushed_at"),
            "topics": repo.get("topics", []),
            "latestRelease": release,
        }

    repos = payload.get("items", [])
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        items = list(executor.map(enrich, repos))
    return envelope(context, "github", items)


def collect_mastodon(context: RunContext) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    url = MASTODON_API + "?limit=" + ("1" if context.dry_run else "40")
    pages = 1 if context.dry_run else 10
    seen: set[str] = set()
    for _ in range(pages):
        payload, headers = request_json(url)
        if not payload:
            break
        oldest_in_window = False
        for status in payload:
            created = status.get("created_at")
            if not in_window(created, context):
                oldest_in_window = True
                continue
            status_url = status.get("url")
            if not status_url or status_url in seen:
                continue
            seen.add(status_url)
            card_url = (status.get("card") or {}).get("url")
            links = [card_url] if card_url else []
            items.append(
                {
                    "author": status.get("account", {}).get("display_name") or status.get("account", {}).get("username"),
                    "handle": "@" + status.get("account", {}).get("acct", ""),
                    "content": strip_html(status.get("content", "")),
                    "url": status_url,
                    "publishedDate": created,
                    "favourites": status.get("favourites_count", 0),
                    "boosts": status.get("reblogs_count", 0),
                    "hasLinks": bool(links),
                    "links": links,
                    "hasMedia": bool(status.get("media_attachments")),
                }
            )
        link = headers.get("Link", "")
        match = re.search(r'<([^>]+)>; rel="next"', link)
        if oldest_in_window or not match:
            break
        url = match.group(1)
    return envelope(context, "mastodon-hachyderm", items)


def browser_eval(session: str, script: str) -> Any:
    result = run(["playwright-cli", f"-s={session}", "eval", script], timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return parse_cli_json(result.stdout)


def browser_collect(
    context: RunContext,
    source: str,
    url: str,
    extraction: str,
    profile_required: bool,
    filter_dates: bool = True,
) -> dict[str, Any]:
    if not shutil.which("playwright-cli"):
        return envelope(context, source, [], status="blocked", error="playwright-cli is not installed")
    profile = ROOT / ".playwright-cli" / "weekly-profiles" / source
    if profile_required and not profile.exists():
        return envelope(
            context,
            source,
            [],
            status="blocked",
            error=f"Login required. Run: python3 .agents/skills/weekly-collect/scripts/login.py {source}",
        )
    session = f"weekly-{source}"
    command = ["playwright-cli", f"-s={session}", "open", url, "--browser=chromium", "--persistent", "--profile", str(profile)]
    opened = run(command, timeout=90)
    if opened.returncode:
        return envelope(context, source, [], status="failed", error=opened.stderr.strip() or opened.stdout.strip())
    try:
        login = browser_eval(session, "() => ({url: location.href, login: !!document.querySelector('input[type=password], [data-testid*=login], form[action*=login], form[action*=signin]')})")
        if profile_required and (login.get("login") or "/login" in login.get("url", "")):
            return envelope(
                context,
                source,
                [],
                status="blocked",
                error=f"Login required. Run: python3 .agents/skills/weekly-collect/scripts/login.py {source}",
            )
        run(["playwright-cli", f"-s={session}", "sleep", "3000"], timeout=10)
        raw_items = browser_eval(session, extraction)
        items = [item for item in raw_items if not filter_dates or in_window(item.get("publishedDate"), context)]
        return envelope(context, source, items, status="ok")
    except Exception as error:
        return envelope(context, source, [], status="partial", error=str(error))
    finally:
        run(["playwright-cli", f"-s={session}", "close"], timeout=20)


BLUESKY_EXTRACTION = r"""() => Array.from(document.querySelectorAll('[data-testid^="feedItem"], article')).slice(0, 100).map(el => { const post = el.querySelector('a[href*="/post/"]'); const links = Array.from(el.querySelectorAll('a[href]')).map(a => a.href).filter(h => h && !h.includes('bsky.app/profile') && !h.includes('bsky.app/hashtag')); return { author: el.querySelector('[data-testid="postAuthor"]')?.innerText?.trim() || '', handle: post?.getAttribute('href')?.split('/')[2] || '', text: el.querySelector('[data-testid="postText"]')?.innerText?.trim() || '', url: post?.href || null, embedUrl: post?.href || null, publishedDate: el.querySelector('time')?.getAttribute('datetime'), likes: 0, reposts: 0, hasLinks: links.length > 0, links, hasImages: !!el.querySelector('img[src*="cdn.bsky.app"]')}; }).filter(x => x.url)"""

TWITTER_EXTRACTION = r"""() => Array.from(document.querySelectorAll('[data-testid="tweet"]')).slice(0, 100).map(el => { const post = el.querySelector('a[href*="/status/"]'); const links = Array.from(el.querySelectorAll('a[href]')).map(a => a.href).filter(h => h && !h.includes('x.com') && !h.includes('twitter.com')); return { author: el.querySelector('[data-testid="User-Name"] span')?.innerText?.trim() || '', handle: '', text: el.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || '', url: post?.href || null, publishedDate: el.querySelector('time')?.getAttribute('datetime'), likes: 0, retweets: 0, isRetweet: false, hasLinks: links.length > 0, links}; }).filter(x => x.url)"""

YOUTUBE_EXTRACTION = r"""() => Array.from(document.querySelectorAll('ytd-video-renderer')).slice(0, 30).map(el => { const a = el.querySelector('a#video-title'); const metadata = Array.from(el.querySelectorAll('#metadata-line span')).map(x => x.innerText.trim()); return { title: a?.innerText?.trim() || '', url: a?.href || null, channel: el.querySelector('#channel-name')?.innerText?.trim() || '', publishedDateText: metadata[1] || '', publishedDate: null, duration: el.querySelector('ytd-thumbnail-overlay-time-status-renderer')?.innerText?.trim() || '', views: metadata[0] || '', thumbnail: el.querySelector('img')?.src || null, source: 'fsharp-search' }; }).filter(x => x.url)"""


def relative_youtube_date(value: str, now: datetime) -> str | None:
    match = re.search(r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", value.lower())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    days = amount * {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30}[unit]
    return (now - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def collect_youtube(context: RunContext) -> dict[str, Any]:
    body, _ = request_bytes(YOUTUBE_DOTNET_FEED)
    root = ET.fromstring(body)
    atom = "{http://www.w3.org/2005/Atom}"
    media = "{http://search.yahoo.com/mrss/}"
    yt = "{http://www.youtube.com/xml/schemas/2015}"
    items: list[dict[str, Any]] = []
    for entry in root.findall(f"{atom}entry"):
        published = entry.findtext(f"{atom}published")
        if not in_window(published, context):
            continue
        group = entry.find(f"{media}group")
        thumbnail = group.find(f"{media}thumbnail").get("url") if group is not None and group.find(f"{media}thumbnail") is not None else None
        items.append(
            {
                "title": entry.findtext(f"{atom}title", ""),
                "url": f"https://www.youtube.com/watch?v={entry.findtext(f'{yt}videoId', '')}",
                "channel": entry.findtext(f"{atom}author/{atom}name", ".NET"),
                "publishedDate": published,
                "duration": None,
                "views": None,
                "thumbnail": thumbnail,
                "source": "dotnet-feed",
            }
        )
        if context.dry_run:
            break

    if not context.dry_run:
        browser = browser_collect(
            context,
            "youtube-search",
            "https://www.youtube.com/results?search_query=F%23&sp=EgQIAxAB",
            YOUTUBE_EXTRACTION,
            False,
            False,
        )
        now = datetime.now(timezone.utc)
        for item in browser.get("items", []):
            item["publishedDate"] = relative_youtube_date(item.pop("publishedDateText", ""), now)
            title = item.get("title", "").lower()
            programming = any(word in title for word in ("f#", "fsharp", ".net", "functional programming", "fable", "ionide"))
            music = any(word in title for word in ("piano", "guitar", "chord", "music", "minor", "major scale"))
            if programming and not music and in_window(item.get("publishedDate"), context):
                items.append(item)
    deduped = list({item["url"]: item for item in items}.values())
    deduped.sort(key=lambda item: item.get("publishedDate") or "", reverse=True)
    return envelope(context, "youtube", deduped)


def collect_bluesky(context: RunContext) -> dict[str, Any]:
    return browser_collect(context, "bluesky", "https://bsky.app/hashtag/fsharp", BLUESKY_EXTRACTION, True)


def collect_twitter(context: RunContext) -> dict[str, Any]:
    return browser_collect(context, "twitter", "https://x.com/hashtag/fsharp?src=hashtag_click&f=live", TWITTER_EXTRACTION, True)


COLLECTORS: dict[str, tuple[str, Callable[[RunContext], dict[str, Any]]]] = {
    "microsoft": ("microsoft-posts.json", collect_microsoft),
    "published": ("published-issues.json", collect_published),
    "nuget": ("nuget-packages.json", collect_nuget),
    "github": ("github-repos.json", collect_github),
    "mastodon": ("mastodon.json", collect_mastodon),
    "youtube": ("youtube-videos.json", collect_youtube),
    "bluesky": ("bluesky.json", collect_bluesky),
    "twitter": ("twitter.json", collect_twitter),
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def execute_source(name: str, context: RunContext) -> tuple[str, dict[str, Any]]:
    filename, collector = COLLECTORS[name]
    try:
        payload = collector(context)
        status = payload.get("status", "ok")
    except Exception as error:
        payload = envelope(context, name, [], status="failed", error=f"{type(error).__name__}: {error}")
        status = "failed"
    write_json(context.output_dir / filename, payload)
    count = len(payload.get("items", payload.get("issues", [])))
    return name, {"status": status, "count": count, "file": filename, "error": payload.get("error")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect F# Weekly source data")
    parser.add_argument("--week", help="Week: 38, week-38, 2026-38, or 2026/38")
    parser.add_argument("--source", choices=sorted(COLLECTORS), help="Collect one source")
    parser.add_argument("--dry-run", action="store_true", help="Fetch at most one page/item per source")
    args = parser.parse_args()
    context = resolve_context(args.week, args.dry_run)
    context.output_dir.mkdir(parents=True, exist_ok=True)
    selected = [args.source] if args.source else list(COLLECTORS)
    print(f"Collecting F# Weekly {context.year}-{context.week:02d} ({context.date_from} to {context.date_to})")

    results: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {executor.submit(execute_source, name, context): name for name in selected}
        for future in concurrent.futures.as_completed(futures):
            name, result = future.result()
            results[name] = result
            suffix = f" - {result['error']}" if result.get("error") else ""
            print(f"{name:10} {result['status']:8} {result['count']:4} {result['file']}{suffix}")

    manifest_path = context.output_dir / "manifest.json"
    existing = {}
    if args.source and manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8")).get("sources", {})
        except (json.JSONDecodeError, OSError):
            pass
    existing.update(results)
    manifest = {
        "generatedAt": iso_now(),
        "year": context.year,
        "weekNumber": context.week,
        "dateFrom": context.date_from.isoformat(),
        "dateTo": context.date_to.isoformat(),
        "dryRun": context.dry_run,
        "sources": existing,
    }
    write_json(manifest_path, manifest)
    print(f"Manifest: {display_path(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
