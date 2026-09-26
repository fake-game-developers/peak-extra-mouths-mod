#!/usr/bin/env python3
"""Copy the live Thunderstore categories into thunderstore.toml before publish."""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    sys.exit("Python 3.11+ is required")

ROOT = Path(__file__).resolve().parents[2]
TOML = ROOT / "src" / "ExtraMouths" / "thunderstore.toml"


def get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "peak-extra-mouths-mod"})
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main() -> int:
    project = tomllib.loads(TOML.read_text(encoding="utf-8"))
    namespace = project["package"]["namespace"]
    name = project["package"]["name"]
    communities = project["publish"]["communities"]

    package_url = f"https://thunderstore.io/api/experimental/package/{namespace}/{name}/"
    try:
        package = get_json(package_url)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            print("Package is not on Thunderstore yet; keeping categories from thunderstore.toml")
            return 0
        raise

    listings = {
        item["community"]: item.get("categories") or []
        for item in package.get("community_listings", [])
    }
    text = TOML.read_text(encoding="utf-8")

    for community in communities:
        names = listings.get(community)
        if not names:
            sys.exit(f"No categories listed for community {community}")
        catalog = get_json(
            f"https://thunderstore.io/api/experimental/community/{community}/category/"
        )
        slug_by_name = {item["name"]: item["slug"] for item in catalog["results"]}
        slugs = []
        for category_name in names:
            slug = slug_by_name.get(category_name)
            if not slug:
                sys.exit(f"No slug for category {category_name!r} in {community}")
            slugs.append(slug)
        line = community + " = [ " + ", ".join(f'"{slug}"' for slug in slugs) + " ]"
        updated, count = re.subn(
            rf"(?m)^{re.escape(community)} = \[.*\]\s*$",
            line,
            text,
            count=1,
        )
        if count != 1:
            sys.exit(f"Could not find a {community} category line in {TOML}")
        text = updated
        print(f"{community}: {', '.join(slugs)}")

    TOML.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
