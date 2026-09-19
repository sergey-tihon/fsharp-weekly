from __future__ import annotations

import argparse
from typing import Any

from common import ROOT, candidate_id, normalize_url, nuget_identity, read_json, resolve_output, write_json


def load_items(folder, filename: str) -> list[dict[str, Any]]:
    payload = read_json(folder / filename, {}) or {}
    return payload.get("items", [])


def display_path(path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def make_candidate(section: str, item: dict[str, Any], title: str, url: str, **extra: Any) -> dict[str, Any]:
    return {"id": candidate_id(section[:3].lower(), normalize_url(url)), "title": title, "url": url, **extra}


def published_sets(folder) -> tuple[set[str], set[tuple[str, str]]]:
    payload = read_json(folder / "published-issues.json", {}) or {}
    urls: set[str] = set()
    packages: set[tuple[str, str]] = set()
    for issue in payload.get("issues", []):
        linked = issue.get("linkedItems") or [{"url": url, "text": ""} for url in issue.get("urls", [])]
        for item in linked:
            url = item.get("url", "")
            urls.add(normalize_url(url))
            identity = nuget_identity(url, item.get("text", ""))
            if identity and identity[1]:
                packages.add((identity[0], identity[1]))
    if not urls:
        urls.update(normalize_url(url) for url in payload.get("allUrls", []))
    return urls, packages


def is_published(candidate: dict[str, Any], urls: set[str], packages: set[tuple[str, str]]) -> bool:
    identity = nuget_identity(candidate["url"], candidate["title"])
    if identity and identity[1]:
        return (identity[0], identity[1]) in packages
    return normalize_url(candidate["url"]) in urls


def prepare(folder) -> dict[str, list[dict[str, Any]]]:
    sections: dict[str, list[dict[str, Any]]] = {
        "news": [],
        "microsoft": [],
        "videos": [],
        "blogs": [],
        "projects": [],
        "releases": [],
        "blueskyEmbeds": [],
    }

    for item in load_items(folder, "microsoft-posts.json"):
        sections["microsoft"].append(make_candidate("microsoft", item, item.get("title", ""), item.get("url", ""), date=item.get("publishedDate")))

    for item in load_items(folder, "youtube-videos.json"):
        sections["videos"].append(
            make_candidate("videos", item, item.get("title", ""), item.get("url", ""), channel=item.get("channel"), date=item.get("publishedDate"))
        )

    social_files = [("mastodon.json", "content"), ("bluesky.json", "text"), ("twitter.json", "text")]
    for filename, text_field in social_files:
        for item in load_items(folder, filename):
            for link in item.get("links", []):
                if not link.startswith(("http://", "https://")):
                    continue
                host = normalize_url(link).split("/")[2]
                if host in {"bsky.app", "x.com", "twitter.com", "hachyderm.io"}:
                    continue
                text = item.get(text_field, "")
                title = " ".join(text.split())[:140] or link
                sections["blogs"].append(make_candidate("blogs", item, title, link, author=item.get("author"), socialUrl=item.get("url")))

    for item in load_items(folder, "github-repos.json"):
        sections["projects"].append(
            make_candidate(
                "projects",
                item,
                item.get("name", ""),
                item.get("url", ""),
                description=item.get("description", ""),
                stars=item.get("stars", 0),
                latestRelease=item.get("latestRelease"),
            )
        )
        release = item.get("latestRelease")
        if release and release.get("releaseUrl"):
            title = f"{item.get('name')} {release.get('tag', '')}".strip()
            sections["releases"].append(make_candidate("releases", item, title, release["releaseUrl"], prerelease=False, downloads=0))

    for item in load_items(folder, "nuget-packages.json"):
        title = f"{item.get('id', '')} {item.get('version', '')}".strip()
        sections["releases"].append(
            make_candidate(
                "releases",
                item,
                title,
                item.get("url", ""),
                packageId=item.get("id"),
                version=item.get("version"),
                prerelease=bool(item.get("isPreRelease")),
                downloads=item.get("totalDownloads", 0),
                downloadsFormatted=item.get("totalDownloadsFormatted", "0"),
            )
        )

    for item in load_items(folder, "bluesky.json"):
        if item.get("embedUrl"):
            sections["blueskyEmbeds"].append(
                make_candidate("bluesky", item, item.get("text", "")[:140], item["embedUrl"], author=item.get("author"), engagement=(item.get("likes", 0) or 0) + (item.get("reposts", 0) or 0))
            )

    urls, packages = published_sets(folder)
    seen: set[str] = set()
    for name, candidates in sections.items():
        filtered = []
        for candidate in candidates:
            key = normalize_url(candidate["url"])
            if not candidate["url"] or key in seen or is_published(candidate, urls, packages):
                continue
            seen.add(key)
            filtered.append(candidate)
        sections[name] = filtered

    sections["projects"].sort(key=lambda item: (bool(item.get("latestRelease")), item.get("stars", 0)), reverse=True)
    sections["releases"].sort(key=lambda item: (item.get("prerelease", False), -item.get("downloads", 0), item["title"].lower()))
    sections["blueskyEmbeds"].sort(key=lambda item: item.get("engagement", 0), reverse=True)
    return sections


def default_editorial(candidates: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    releases = [item for item in candidates["releases"] if not item.get("prerelease") or item.get("downloads", 0) > 10_000]
    if any((item.get("packageId") or "").lower() == "fsharp.data" for item in releases):
        releases = [item for item in releases if not (item.get("packageId") or "").lower().startswith("fsharp.data.")]
    return {
        "title": "",
        "intro": "",
        "sections": {
            "news": [],
            "microsoft": [item["id"] for item in candidates["microsoft"]],
            "videos": [item["id"] for item in candidates["videos"]],
            "blogs": [item["id"] for item in candidates["blogs"]],
            "projects": [item["id"] for item in candidates["projects"][:5]],
            "releases": [item["id"] for item in releases],
        },
        "blueskyEmbeds": [item["id"] for item in candidates["blueskyEmbeds"][:3]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare newsletter candidates")
    parser.add_argument("--week")
    args = parser.parse_args()
    year, week, folder = resolve_output(args.week)
    if not folder.exists():
        parser.error(f"No data found at {display_path(folder)}. Run /weekly first.")
    candidates = prepare(folder)
    write_json(folder / "candidates.json", {"year": year, "weekNumber": week, "sections": candidates})
    write_json(folder / "editorial.json", default_editorial(candidates))
    print(f"Prepared candidates for {year}-{week:02d}")
    for name, items in candidates.items():
        print(f"{name:16} {len(items):4}")
    print(f"Edit: {display_path(folder / 'editorial.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
