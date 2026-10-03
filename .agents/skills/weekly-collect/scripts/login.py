from __future__ import annotations

import argparse
import shutil
import subprocess

from common import ROOT


URLS = {
    "bluesky": "https://bsky.app/hashtag/fsharp",
    "twitter": "https://x.com/hashtag/fsharp?src=hashtag_click&f=live",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a persistent browser login for an optional social source")
    parser.add_argument("source", choices=sorted(URLS))
    args = parser.parse_args()
    if not shutil.which("playwright-cli"):
        parser.error("playwright-cli is not installed")

    profile = ROOT / ".playwright-cli" / "weekly-profiles" / args.source
    profile.parent.mkdir(parents=True, exist_ok=True)
    session = f"weekly-login-{args.source}"
    command = [
        "playwright-cli",
        f"-s={session}",
        "open",
        URLS[args.source],
        "--browser=chromium",
        "--headed",
        "--persistent",
        "--profile",
        str(profile),
    ]
    opened = subprocess.run(command, cwd=ROOT, check=False)
    if opened.returncode:
        return opened.returncode
    input(f"Log in to {args.source} in the browser, then press Enter here... ")
    subprocess.run(["playwright-cli", f"-s={session}", "close"], cwd=ROOT, check=False)
    print(f"Saved browser profile: {profile.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
