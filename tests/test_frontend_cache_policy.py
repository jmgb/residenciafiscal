"""Política de caché del sitio estático.

Un móvil que conserva la pestaña abierta durante días es el caso normal, no el
raro: la SPA solo vuelve a pedir el HTML si el navegador decide revalidar. Estas
reglas son las que impiden que ese navegador se quede clavado en un deploy
antiguo, y una de ellas evita además que una respuesta rota se cachee un año.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parents[1]


def _config() -> dict[str, Any]:
    return tomllib.loads((PROJECT_ROOT / "netlify.toml").read_text(encoding="utf-8"))


def _headers_for(path: str) -> dict[str, str]:
    for block in _config()["headers"]:
        if block["for"] == path:
            return dict(block["values"])
    raise AssertionError(f"no hay bloque [[headers]] para {path!r} en netlify.toml")


def _redirect_index(predicate: Any) -> int:
    redirects = _config()["redirects"]
    for index, redirect in enumerate(redirects):
        if predicate(redirect):
            return index
    raise AssertionError("no existe la redirección buscada en netlify.toml")


def test_missing_assets_return_404_instead_of_the_spa_shell() -> None:
    """Sin esta regla, un chunk borrado devuelve la shell HTML con 200.

    El fallback `/* → /index.html` también captura `/assets/*`, y el bloque de
    cabeceras de `/assets/*` marca la respuesta `immutable` durante un año: el
    navegador guarda HTML disfrazado de JavaScript y la app queda rota en ese
    dispositivo hasta que caduque la caché.
    """
    redirects = _config()["redirects"]

    assets = _redirect_index(lambda redirect: redirect["from"] == "/assets/*")
    fallback = _redirect_index(lambda redirect: redirect["from"] == "/*")

    assert redirects[assets]["status"] == 404
    assert assets < fallback


def test_missing_data_files_return_404_instead_of_the_spa_shell() -> None:
    """El corpus y los preceptos se piden con `fetch` y se parsean como JSON.

    Con el fallback activo, un fichero ausente devuelve HTML con 200 y el
    parseo falla por una razón que no se parece en nada a la real.
    """
    redirects = _config()["redirects"]

    data = _redirect_index(lambda redirect: redirect["from"] == "/data/*")
    fallback = _redirect_index(lambda redirect: redirect["from"] == "/*")

    assert redirects[data]["status"] == 404
    assert data < fallback


def test_the_404_destination_is_published() -> None:
    """Las reglas de 404 apuntan a un fichero: si no existe, Netlify no lo sirve."""
    targets = {
        redirect["to"] for redirect in _config()["redirects"] if redirect.get("status") == 404
    }

    assert targets == {"/404.html"}
    assert (PROJECT_ROOT / "frontend" / "public" / "404.html").is_file()


def test_hashed_assets_stay_immutable() -> None:
    """El nombre lleva hash: cachearlos para siempre es correcto y necesario."""
    assert _headers_for("/assets/*")["Cache-Control"] == "public, max-age=31536000, immutable"


def test_the_html_entrypoint_revalidates_on_every_visit() -> None:
    """Netlify hace match por la ruta pedida, no por el fichero servido.

    Por eso una regla para `/index.html` no cubre a quien entra por `/`, que es
    todo el mundo. Se declaran las dos.
    """
    for path in ("/", "/index.html"):
        cache_control = _headers_for(path)["Cache-Control"]
        assert "max-age=0" in cache_control
        assert "must-revalidate" in cache_control
        # `no-store` desactivaría también el back/forward cache del móvil, que sí
        # queremos conservar: la comprobación de versión en runtime lo cubre.
        assert "no-store" not in cache_control


def test_the_data_files_are_revalidated_instead_of_frozen_for_an_hour() -> None:
    """`max-age=3600` garantizaba hasta una hora de corpus viejo tras un deploy.

    Los ficheros tienen ETag, así que revalidar cuesta un 304 vacío. La regla
    cubre `/data/*` —corpus, normativa y preceptos— porque los tres se
    regeneran en el mismo build y ninguno lleva hash en el nombre.
    """
    cache_control = _headers_for("/data/*")["Cache-Control"]

    assert "max-age=0" in cache_control
    assert "must-revalidate" in cache_control


def test_the_version_manifest_is_never_cached() -> None:
    """Es el fichero que delata que hay un deploy nuevo: cachearlo lo inutiliza."""
    cache_control = _headers_for("/version.json")["Cache-Control"]

    assert "no-store" in cache_control


def test_the_root_redirects_to_the_spain_landing() -> None:
    """La raíz servía la shell sin contenido y no era canónica de nada.

    El prerenderizado escribe una copia por ruta en su subdirectorio, pero no
    toca `dist/index.html`: quien pedía `/` sin ejecutar JavaScript no recibía
    ni una línea de texto, y la página declaraba `canonical` hacia sí misma sin
    estar en el sitemap. Con el `301`, la home del sitio pasa a ser `/espana`,
    que es la que ya publica el sitemap con prioridad `1.0`.

    `force` es obligatorio: `dist/index.html` existe, y Netlify sirve el fichero
    antes que una redirección que no lo lleve.
    """
    redirects = _config()["redirects"]
    index = _redirect_index(lambda redirect: redirect["from"] == "/")

    assert redirects[index]["to"] == "/espana"
    assert redirects[index]["status"] == 301
    assert redirects[index]["force"] is True

    # Netlify aplica la primera coincidencia: detrás del fallback la regla sería
    # inalcanzable, porque `/*` captura también la raíz.
    fallback = _redirect_index(lambda redirect: redirect["from"] == "/*")
    assert index < fallback
