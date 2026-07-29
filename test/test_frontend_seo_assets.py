from __future__ import annotations

import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

FRONTEND_PUBLIC = Path(__file__).parents[1] / "frontend" / "public"
PROJECT_ROOT = Path(__file__).parents[1]
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


def test_sitemap_contains_only_the_canonical_public_routes() -> None:
    root = ET.parse(FRONTEND_PUBLIC / "sitemap.xml").getroot()
    raw_locations = [node.text for node in root.findall("sm:url/sm:loc", SITEMAP_NAMESPACE)]
    assert all(location is not None for location in raw_locations)
    locations = [location for location in raw_locations if location is not None]

    assert locations == [
        "https://residenciafiscal.org/",
        "https://residenciafiscal.org/manifiesto",
        "https://residenciafiscal.org/metodologia",
    ]
    assert all("?" not in location and "#" not in location for location in locations)
    # Las conversaciones (/c/) son privadas: nunca entran en el sitemap.
    assert all("/c/" not in location for location in locations)


def test_llms_txt_describes_the_public_corpus_without_private_routes() -> None:
    llms = (FRONTEND_PUBLIC / "llms.txt").read_text(encoding="utf-8")

    assert llms.startswith("# Residencia Fiscal")
    assert "106 sentencias" in llms
    assert "https://residenciafiscal.org/" in llms
    assert "/c/" not in llms


def test_public_routes_serve_their_prerender_before_the_spa_fallback() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirects = config["redirects"]

    assert redirects[:2] == [
        {
            "from": "/manifiesto",
            "to": "/manifiesto/index.html",
            "status": 200,
            "force": True,
        },
        {
            "from": "/metodologia",
            "to": "/metodologia/index.html",
            "status": 200,
            "force": True,
        },
    ]
    assert redirects[-1] == {"from": "/*", "to": "/index.html", "status": 200}
