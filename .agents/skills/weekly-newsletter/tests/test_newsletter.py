import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from common import normalize_url, nuget_identity

prepare_spec = importlib.util.spec_from_file_location("weekly_prepare", SCRIPT_DIR / "prepare.py")
prepare = importlib.util.module_from_spec(prepare_spec)
prepare_spec.loader.exec_module(prepare)

render_spec = importlib.util.spec_from_file_location("weekly_render", SCRIPT_DIR / "render.py")
render = importlib.util.module_from_spec(render_spec)
render_spec.loader.exec_module(render)


class NormalizationTests(unittest.TestCase):
    def test_removes_fragment_tracking_and_trailing_slash(self):
        self.assertEqual(
            "https://example.com/Post?a=1",
            normalize_url("https://EXAMPLE.com/Post/?utm_source=x&a=1#part"),
        )

    def test_reads_nuget_version_from_link_text(self):
        self.assertEqual(
            ("fantomas", "8.0.0"),
            nuget_identity("https://www.nuget.org/packages/fantomas", "Fantomas 8.0.0"),
        )

    def test_matches_versioned_candidate_to_unversioned_published_link(self):
        candidate = {"url": "https://www.nuget.org/packages/fantomas/8.0.0", "title": "fantomas 8.0.0"}
        self.assertTrue(prepare.is_published(candidate, set(), {("fantomas", "8.0.0")}))


class RenderTests(unittest.TestCase):
    def test_rejects_unknown_ids(self):
        candidates = {"sections": {name: [] for name in [*render.SECTION_LABELS, "blueskyEmbeds"]}}
        editorial = {
            "title": "Title",
            "intro": "Intro",
            "sections": {"news": ["missing"]},
            "blueskyEmbeds": [],
        }
        with self.assertRaisesRegex(ValueError, "news:missing"):
            render.validate(candidates, editorial)

    def test_render_is_deterministic(self):
        item = {"id": "mic-1", "title": "A & B", "url": "https://example.com/?a=1&b=2"}
        candidates = {"sections": {name: [] for name in [*render.SECTION_LABELS, "blueskyEmbeds"]}}
        candidates["sections"]["microsoft"] = [item]
        editorial = {
            "title": "Title",
            "intro": "Intro",
            "sections": {"microsoft": ["mic-1"]},
            "blueskyEmbeds": [],
        }
        indexes = render.validate(candidates, editorial)
        self.assertEqual(render.render_html(2026, 38, editorial, indexes), render.render_html(2026, 38, editorial, indexes))


if __name__ == "__main__":
    unittest.main()
