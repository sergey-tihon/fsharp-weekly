from __future__ import annotations

import argparse
import html
from typing import Any

from common import ROOT, read_json, resolve_output


SECTION_LABELS = {
    "news": "News",
    "microsoft": "Microsoft News",
    "videos": "Videos",
    "blogs": "Blogs",
    "projects": "Highlighted projects",
    "releases": "New Releases",
}


def display_path(path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate(candidates: dict[str, Any], editorial: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not editorial.get("title", "").strip():
        raise ValueError("editorial.title is required")
    if not editorial.get("intro", "").strip():
        raise ValueError("editorial.intro is required")
    indexes = {name: {item["id"]: item for item in items} for name, items in candidates["sections"].items()}
    unknown = []
    for section in SECTION_LABELS:
        for item_id in editorial.get("sections", {}).get(section, []):
            if item_id not in indexes.get(section, {}):
                unknown.append(f"{section}:{item_id}")
    embeds = editorial.get("blueskyEmbeds", [])
    if len(embeds) > 3:
        raise ValueError("blueskyEmbeds may contain at most 3 IDs")
    for item_id in embeds:
        if item_id not in indexes.get("blueskyEmbeds", {}):
            unknown.append(f"blueskyEmbeds:{item_id}")
    if unknown:
        raise ValueError("Unknown candidate IDs: " + ", ".join(unknown))
    return indexes


def selected(editorial: dict[str, Any], indexes: dict[str, dict[str, Any]], section: str) -> list[dict[str, Any]]:
    return [indexes[section][item_id] for item_id in editorial.get("sections", {}).get(section, [])]


def item_text(item: dict[str, Any], section: str) -> str:
    title = item["title"]
    if section == "projects" and item.get("description"):
        return f"{title}: {item['description']}"
    if section == "blogs" and item.get("author"):
        return f"{item['author']}: {title}"
    return title


def render_html(year: int, week: int, editorial: dict[str, Any], indexes: dict[str, dict[str, Any]]) -> str:
    blocks = [
        "<!-- wp:paragraph -->\n<p>Welcome to F# Weekly,</p>\n<!-- /wp:paragraph -->",
        "<!-- wp:paragraph -->\n<p>A roundup of F# content from this past week:</p>\n<!-- /wp:paragraph -->",
        f"<!-- wp:paragraph -->\n<p>{html.escape(editorial['intro'])}</p>\n<!-- /wp:paragraph -->",
    ]
    embeds = [indexes["blueskyEmbeds"][item_id] for item_id in editorial.get("blueskyEmbeds", [])]
    embed_positions = {"news": 0, "blogs": 1, "releases": 2}
    for section, label in SECTION_LABELS.items():
        items = selected(editorial, indexes, section)
        if not items:
            continue
        lines = []
        for item in items:
            lines.append(f'  <!-- wp:list-item -->\n  <li><a href="{html.escape(item["url"], quote=True)}">{html.escape(item_text(item, section))}</a></li>\n  <!-- /wp:list-item -->')
        blocks.append(f"<!-- wp:paragraph -->\n<p><strong>{label}</strong></p>\n<!-- /wp:paragraph -->")
        blocks.append("<!-- wp:list -->\n<ul class=\"wp-block-list\">\n" + "\n".join(lines) + "\n</ul>\n<!-- /wp:list -->")
        index = embed_positions.get(section)
        if index is not None and index < len(embeds):
            url = html.escape(embeds[index]["url"], quote=True)
            blocks.append(
                f'<!-- wp:embed {{"url":"{url}","type":"rich","providerNameSlug":"bluesky-social"}} -->\n'
                '<figure class="wp-block-embed is-type-rich is-provider-bluesky-social wp-block-embed-bluesky-social">\n'
                f'  <div class="wp-block-embed__wrapper">{url}</div>\n'
                '</figure>\n<!-- /wp:embed -->'
            )
    blocks.extend(
        [
            "<!-- wp:paragraph -->\n<p>That's all for now. Have a great week.</p>\n<!-- /wp:paragraph -->",
            '<!-- wp:paragraph -->\n<p>If you want to help keep F# Weekly going, <a href="https://www.buymeacoffee.com/sergeytihon">click here to jazz me with Coffee</a>!</p>\n<!-- /wp:paragraph -->',
            '<p align="right"><a href="https://www.buymeacoffee.com/sergeytihon" target="_blank" rel="noopener"><img class="alignnone" style="height: 60px !important; width: 217px !important" src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="211" height="60" /></a></p>',
        ]
    )
    return "\n\n".join(blocks) + "\n"


def render_markdown(year: int, week: int, editorial: dict[str, Any], indexes: dict[str, dict[str, Any]], generated_at: str | None = None) -> str:
    lines = [f"# F# Weekly #{week}, {year} - {editorial['title']}", "", "Welcome to F# Weekly,", "", "A roundup of F# content from this past week:", "", editorial["intro"]]
    for section, label in SECTION_LABELS.items():
        items = selected(editorial, indexes, section)
        if not items:
            continue
        lines.extend(["", "---", "", f"## {label}", ""])
        for item in items:
            suffix = ""
            if section == "videos" and item.get("channel"):
                suffix = f" - {item['channel']}"
            if section == "releases" and item.get("downloadsFormatted"):
                suffix = f" - {item['downloadsFormatted']} downloads"
            lines.append(f"- [{item_text(item, section)}]({item['url']}){suffix}")
    embeds = [indexes["blueskyEmbeds"][item_id] for item_id in editorial.get("blueskyEmbeds", [])]
    if embeds:
        lines.extend(["", "---", "", "*Selected Bluesky posts this week:*", ""])
        lines.extend(f"- {item['url']}" for item in embeds)
    if generated_at:
        lines.extend(["", "---", "", f"*Generated: {generated_at}*", ""])
    else:
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render newsletter drafts")
    parser.add_argument("--week")
    args = parser.parse_args()
    year, week, folder = resolve_output(args.week)
    candidates = read_json(folder / "candidates.json")
    editorial = read_json(folder / "editorial.json")
    if not candidates or not editorial:
        parser.error("Missing candidates.json or editorial.json. Run prepare.py first.")
    try:
        indexes = validate(candidates, editorial)
    except ValueError as error:
        parser.error(str(error))
    html_output = render_html(year, week, editorial, indexes)
    generated_at = (read_json(folder / "manifest.json", {}) or {}).get("generatedAt")
    markdown_output = render_markdown(year, week, editorial, indexes, generated_at)
    (folder / "newsletter-draft.html").write_text(html_output, encoding="utf-8")
    (folder / "newsletter-draft.md").write_text(markdown_output, encoding="utf-8")
    print(f"Rendered F# Weekly #{week}, {year}: {editorial['title']}")
    for section in SECTION_LABELS:
        print(f"{section:12} {len(editorial.get('sections', {}).get(section, [])):4}")
    print(f"bluesky       {len(editorial.get('blueskyEmbeds', [])):4}")
    print(f"Output: {display_path(folder / 'newsletter-draft.html')}")
    print(f"Output: {display_path(folder / 'newsletter-draft.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
