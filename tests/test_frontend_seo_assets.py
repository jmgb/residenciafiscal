from __future__ import annotations

import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

FRONTEND_PUBLIC = Path(__file__).parents[1] / "frontend" / "public"
PROJECT_ROOT = Path(__file__).parents[1]
SITEMAP_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _robots_groups() -> dict[str, list[str]]:
    """Agrupa `robots.txt` por user-agent para poder afirmar sobre cada bloque.

    El fichero se leía antes con `in`, y `assert "Allow: /" in robots` se cumplía
    aunque el grupo comprobado no tuviera ninguna directiva: bastaba con que
    apareciera en cualquier otro sitio del fichero.
    """
    groups: dict[str, list[str]] = {}
    current: list[str] | None = None
    for raw_line in (FRONTEND_PUBLIC / "robots.txt").read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        field, _, value = line.partition(":")
        name = field.strip().lower()
        if name == "user-agent":
            current = groups.setdefault(value.strip(), [])
        elif name == "sitemap":
            # `Sitemap` es una directiva de fichero, no de grupo: no pertenece al
            # último user-agent declarado aunque venga detrás de él.
            current = None
        elif current is not None:
            current.append(line)
    return groups


# Agentes de asistentes y buscadores generativos que deben poder rastrear el
# sitio. Los `*-User` no rastrean: descargan la página que alguien acaba de
# pedir en el asistente, y sin su grupo propio pierden el Disallow de /c/.
AI_AGENTS = (
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Google-CloudVertexBot",
    "Applebot-Extended",
    "meta-externalagent",
    "MistralAI-User",
    "DuckAssistBot",
    "cohere-ai",
    "Amazonbot",
    "CCBot",
)


def test_robots_allows_public_content_and_declares_seo_assets() -> None:
    robots = (FRONTEND_PUBLIC / "robots.txt").read_text(encoding="utf-8")
    groups = _robots_groups()

    assert groups["*"] == ["Allow: /", "Disallow: /c/"]
    assert "Sitemap: https://residenciafiscal.org/sitemap.xml" in robots
    # El resumen para agentes solo sirve si se puede descubrir desde robots.txt.
    assert "https://residenciafiscal.org/llms.txt" in robots


def test_robots_lets_every_declared_ai_agent_crawl_everything_but_conversations() -> None:
    groups = _robots_groups()

    for agent in AI_AGENTS:
        assert agent in groups, f"{agent} no tiene grupo propio en robots.txt"
        # Un grupo específico no hereda del grupo `*`: si le falta el Disallow,
        # el agente puede rastrear las conversaciones privadas.
        assert groups[agent] == ["Allow: /", "Disallow: /c/"], agent


def test_sitemap_contains_only_the_canonical_public_routes() -> None:
    root = ET.parse(FRONTEND_PUBLIC / "sitemap.xml").getroot()
    raw_locations = [node.text for node in root.findall("sm:url/sm:loc", SITEMAP_NAMESPACE)]
    assert all(location is not None for location in raw_locations)
    locations = [location for location in raw_locations if location is not None]

    # Todas las rutas de país entran: cada una publica el convenio de doble
    # imposición entre España y esa jurisdicción, con su enlace al BOE, así que
    # tienen contenido propio que indexar. Después entran las rutas estáticas
    # indexables (`/privacidad` sigue fuera) y una ficha por precepto del
    # corpus normativo, que publica el texto literal del BOE.
    rutas_pais = [
        ruta["path"]
        for ruta in json.loads(
            (PROJECT_ROOT / "frontend" / "src" / "data" / "countryRoutes.json").read_text(
                encoding="utf-8"
            )
        )
    ]
    rutas_estaticas = [
        ruta["path"]
        for ruta in json.loads(
            (PROJECT_ROOT / "frontend" / "src" / "data" / "staticRoutes.json").read_text(
                encoding="utf-8"
            )
        )
        if ruta["indexable"]
    ]
    rutas_preceptos = [
        f"/espana/normativa/{precepto['slug']}"
        for precepto in json.loads(
            (FRONTEND_PUBLIC / "data" / "normativa.json").read_text(encoding="utf-8")
        )
    ]
    assert "/espana/normativa" in rutas_estaticas
    assert "/privacidad" not in rutas_estaticas
    assert len(rutas_preceptos) >= 110
    assert locations == [
        f"https://residenciafiscal.org{path}"
        for path in [*rutas_pais, *rutas_estaticas, *rutas_preceptos]
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
    # llms.txt es donde un asistente lee que el corpus de otro país todavía no
    # existe y que se puede contribuir, en vez de inventarse jurisprudencia que
    # no tenemos. Ahora esas páginas se indexan, así que también tiene que decir
    # qué sí publican: el convenio de doble imposición con España.
    assert "https://residenciafiscal.org/colaborar" in llms
    assert "contribución de expertos" in llms
    assert "convenio de doble imposición" in llms.lower()


def test_public_routes_serve_their_prerender_before_the_spa_fallback() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirects = config["redirects"]

    redirect_pairs = {(redirect["from"], redirect["to"]) for redirect in redirects}
    for path in ("/manifiesto", "/metodologia", "/espana/fuentes", "/colaborar", "/privacidad"):
        assert (path, f"{path}/index.html") in redirect_pairs
    assert redirects[-1] == {"from": "/*", "to": "/404.html", "status": 404}


def test_spa_only_routes_keep_serving_the_shell_before_the_404_fallback() -> None:
    """`/consulta` y `/c/:id` no tienen fichero físico: sin regla propia, el
    fallback 404 las mataría. Deben servir la shell con 200 y quedar antes."""
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirects = config["redirects"]

    fallback = redirects.index(next(r for r in redirects if r["from"] == "/*"))
    for path in ("/consulta", "/c/*"):
        rule = next(r for r in redirects if r["from"] == path)
        assert rule["to"] == "/index.html"
        assert rule["status"] == 200
        assert redirects.index(rule) < fallback


def test_unknown_routes_are_a_real_404_not_a_soft_404() -> None:
    """Antes cualquier ruta inexistente devolvía la shell con 200, `robots`
    index y canonical hacia `/` (que además redirige): un soft 404 por URL."""
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    fallback = config["redirects"][-1]

    assert fallback == {"from": "/*", "to": "/404.html", "status": 404}


def test_the_spa_shell_is_not_indexable() -> None:
    """Desde que `/` redirige a `/espana`, la shell no es ninguna página
    pública: solo la sirven `/consulta` y `/c/*`. El prerender reescribe la
    meta `robots` de cada ruta real, así que puede ser `noindex` sin coste."""
    shell = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert '<meta name="robots" content="noindex, follow" />' in shell
    assert '<meta name="robots" content="index, follow" />' not in shell


def test_collaborate_route_serves_its_prerender() -> None:
    config = tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))
    redirect_pairs = {(redirect["from"], redirect["to"]) for redirect in config["redirects"]}

    assert ("/colaborar", "/colaborar/index.html") in redirect_pairs


def test_country_routes_have_prerender_redirects() -> None:
    routes = json.loads(
        (PROJECT_ROOT / "frontend" / "src" / "data" / "countryRoutes.json").read_text(
            encoding="utf-8"
        )
    )
    expected_lines = [
        "# Generated by frontend/scripts/build-netlify-redirects.mjs.",
        "# Source: frontend/src/data/countryRoutes.json + public/data/normativa.json.",
    ]
    for route in routes:
        legacy_path = "/" + re.sub(r"\s+", "-", route["name"].lower())
        if legacy_path != route["path"]:
            expected_lines.append(f"{quote(legacy_path, safe='/')} {route['path']} 301!")
    for route in routes:
        expected_lines.append(f"{route['path']} {route['path']}/index.html 200!")
    # Las fichas de precepto también sirven su copia prerenderizada: sin regla
    # propia, el fallback 404 las mataría si el fichero físico no ganara.
    expected_lines.append("/espana/normativa /espana/normativa/index.html 200!")
    for precepto in json.loads(
        (FRONTEND_PUBLIC / "data" / "normativa.json").read_text(encoding="utf-8")
    ):
        slug = precepto["slug"]
        expected_lines.append(f"/espana/normativa/{slug} /espana/normativa/{slug}/index.html 200!")

    redirects_file = FRONTEND_PUBLIC / "_redirects"
    assert redirects_file.read_text(encoding="utf-8").splitlines() == expected_lines
