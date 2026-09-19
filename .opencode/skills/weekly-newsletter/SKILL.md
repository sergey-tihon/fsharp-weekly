---
name: weekly-newsletter
description: Prepares and renders an F# Weekly newsletter. Use after weekly-collect, for /update, or when editing a newsletter draft.
---

# Weekly Newsletter

Run from the repository root. Omit `--week` when no week argument was supplied.

1. Prepare deduplicated candidates and an initial editorial file:

```bash
python3 .opencode/skills/weekly-newsletter/scripts/prepare.py --week "$ARGUMENTS"
```

2. Read `data/{year}/week-{NN}/candidates.json` and `editorial.json`. Edit only `editorial.json`:

- Write an accurate `title` without the `F# Weekly #NN` prefix.
- Write a 1-3 sentence `intro`.
- Reorder, add, or remove candidate IDs in sections.
- Use only IDs present in `candidates.json`.
- Select up to 3 `blueskyEmbeds`; an empty list is valid.
- Keep News empty unless an item is genuinely major F# news.

Detailed editorial guidance is in `references/editorial-rules.md`.

3. Validate and render both formats:

```bash
python3 .opencode/skills/weekly-newsletter/scripts/render.py --week "$ARGUMENTS"
```

The renderer writes `newsletter-draft.html` and `newsletter-draft.md`. If validation fails, fix `editorial.json` using the exact error and rerun the renderer.
