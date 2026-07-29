from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

FRONTEND_PUBLIC = Path(__file__).parents[1] / "frontend" / "public"
SITEMAP_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def test_robots_allows_public_content_and_declares_seo_assets() -> None:
    robots = (FRONTEND_PUBLIC / "robots.txt").read_text(encoding="utf-8")

    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "Disallow: /c/" in robots
    assert "Sitemap: https://residenciafiscal.org/sitemap.xml" in robots

    for crawler in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot"):
        assert f"User-agent: {crawler}" in robots
        assert "Allow: /" in robots


def test_sitemap_contains_only_the_canonical_public_home() -> None:
    root = ET.parse(FRONTEND_PUBLIC / "sitemap.xml").getroot()
    locations = [node.text for node in root.findall("sm:url/sm:loc", SITEMAP_NAMESPACE)]

    assert locations == ["https://residenciafiscal.org/"]
    assert all("?" not in location and "#" not in location for location in locations)


def test_llms_txt_describes_the_public_corpus_without_private_routes() -> None:
    llms = (FRONTEND_PUBLIC / "llms.txt").read_text(encoding="utf-8")

    assert llms.startswith("# Residencia Fiscal")
    assert "106 sentencias" in llms
    assert "https://residenciafiscal.org/" in llms
    assert "/c/" not in llms
