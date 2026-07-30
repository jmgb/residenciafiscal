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

    # `/colaborar` es la única puerta indexable de la invitación a contribuir: las
    # páginas de país sin corpus son `noindex`, así que sin esta URL la invitación
    # no se puede encontrar desde una búsqueda.
    assert locations == [
        "https://residenciafiscal.org/espana",
        "https://residenciafiscal.org/manifiesto",
        "https://residenciafiscal.org/metodologia",
        "https://residenciafiscal.org/colaborar",
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
    # Con las páginas de país en `noindex`, llms.txt es la vía por la que un
    # asistente puede decir que el corpus de otro país todavía no existe y que se
    # puede contribuir, en vez de inventarse jurisprudencia que no tenemos.
    assert "https://residenciafiscal.org/colaborar" in llms
    assert "contribución de expertos" in llms


def test_public_routes_serve_their_prerender_before_the_spa_fallback() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirects = config["redirects"]

    assert redirects[:7] == [
        {
            "from": "/españa",
            "to": "/espana",
            "status": 301,
            "force": True,
        },
        {
            "from": "/haití",
            "to": "/haiti",
            "status": 301,
            "force": True,
        },
        {
            "from": "/méxico",
            "to": "/mexico",
            "status": 301,
            "force": True,
        },
        {
            "from": "/panamá",
            "to": "/panama",
            "status": 301,
            "force": True,
        },
        {
            "from": "/perú",
            "to": "/peru",
            "status": 301,
            "force": True,
        },
        {
            "from": "/república-dominicana",
            "to": "/republica-dominicana",
            "status": 301,
            "force": True,
        },
        {
            "from": "/espana",
            "to": "/espana/index.html",
            "status": 200,
            "force": True,
        },
    ]
    assert redirects[-1] == {"from": "/*", "to": "/index.html", "status": 200}


def test_collaborate_route_serves_its_prerender() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirect_pairs = {(redirect["from"], redirect["to"]) for redirect in config["redirects"]}

    assert ("/colaborar", "/colaborar/index.html") in redirect_pairs


def test_country_routes_have_prerender_redirects() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirects = config["redirects"]
    redirect_pairs = {(redirect["from"], redirect["to"]) for redirect in redirects}

    for path in (
        "/espana",
        "/estados-unidos",
        "/portugal",
        "/francia",
        "/reino-unido",
        "/alemania",
        "/suiza",
        "/andorra",
        "/italia",
        "/argentina",
        "/bolivia",
        "/brasil",
        "/chile",
        "/colombia",
        "/costa-rica",
        "/cuba",
        "/ecuador",
        "/el-salvador",
        "/guatemala",
        "/haiti",
        "/honduras",
        "/mexico",
        "/nicaragua",
        "/panama",
        "/paraguay",
        "/peru",
        "/republica-dominicana",
        "/uruguay",
        "/venezuela",
    ):
        assert (path, f"{path}/index.html") in redirect_pairs

    for legacy_path, canonical_path in (
        ("/españa", "/espana"),
        ("/haití", "/haiti"),
        ("/méxico", "/mexico"),
        ("/panamá", "/panama"),
        ("/perú", "/peru"),
        ("/república-dominicana", "/republica-dominicana"),
    ):
        assert (legacy_path, canonical_path) in redirect_pairs
