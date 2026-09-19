import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from common import resolve_context

collect_spec = importlib.util.spec_from_file_location("weekly_collect", SCRIPT_DIR / "collect.py")
collect = importlib.util.module_from_spec(collect_spec)
collect_spec.loader.exec_module(collect)


class ResolveContextTests(unittest.TestCase):
    def test_uses_iso_year_at_new_year(self):
        context = resolve_context(None, today=date(2027, 1, 1))
        self.assertEqual((2026, 53), (context.year, context.week))

    def test_parses_supported_year_week_formats(self):
        for value in ("2026-38", "2026/38"):
            with self.subTest(value=value):
                context = resolve_context(value, today=date(2026, 9, 19))
                self.assertEqual((2026, 38), (context.year, context.week))

    def test_rejects_invalid_week(self):
        with self.assertRaises(ValueError):
            resolve_context("2026-99")


class NuGetParsingTests(unittest.TestCase):
    def test_parses_recent_results_page(self):
        page = """
        <li class="package">
          <a data-package-id="Fantomas" data-package-version="8.0.0"></a>
          <span>1,234 total downloads</span>
          <span data-datetime="2026-09-15T10:19:05+00:00"></span>
          <a title="Search for F#">F#</a>
          <div class="package-details">F# formatter</div>
        </li>
        """
        self.assertEqual(
            {
                "id": "Fantomas",
                "version": "8.0.0",
                "publishedDate": "2026-09-15T10:19:05+00:00",
                "description": "F# formatter",
                "totalDownloads": 1234,
                "totalDownloadsFormatted": "1,234",
                "isPreRelease": False,
                "url": "https://www.nuget.org/packages/Fantomas/8.0.0",
                "tags": ["F#"],
            },
            collect.parse_nuget_page(page)[0],
        )


if __name__ == "__main__":
    unittest.main()
