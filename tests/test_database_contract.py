"""El manifiesto de firmas no puede quedarse atrás respecto a las migraciones.

`check-database-contract.sh` compara el manifiesto con la base de datos viva,
pero eso solo detecta la deriva si el manifiesto dice lo que dice el repositorio.
Estos tests atan el otro extremo: el manifiesto contra el SQL versionado y
contra lo que producción invoca de verdad —timers del VPS, Function del chat y
prototipo FastAPI—, para que no pueda perder cobertura en silencio.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
BACKUP_DIR = PROJECT_ROOT / "scripts" / "backup"
MANIFEST = BACKUP_DIR / "database-contract.txt"
MIGRATIONS = sorted((PROJECT_ROOT / "supabase" / "migrations").glob("*.sql"))
# Todo lo que llama a una RPC en producción: los timers del VPS, la Function del
# chat y el prototipo FastAPI. Si el manifiesto pudiera no cubrir a alguno,
# perdería cobertura en silencio, que es justo lo que vino a impedir.
CONSUMIDORES = [
    *sorted(BACKUP_DIR.glob("*.sh")),
    *sorted((PROJECT_ROOT / "scripts" / "privacy").glob("*.sh")),
    *sorted((PROJECT_ROOT / "scripts").glob("*.py")),
    *sorted((PROJECT_ROOT / "frontend" / "netlify" / "functions").rglob("*.ts")),
    *sorted((PROJECT_ROOT / "src" / "api").rglob("*.py")),
]
DECLARACION = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?P<funcion>(?:public|private)\.[a-z][a-z0-9_]*)\s*\(",
    re.IGNORECASE,
)
# Tres formas de llamar: `private.f(` en SQL suelto, y por REST o por cliente
# desde el runtime. PostgREST solo expone `public`, así que ahí el schema se da.
LLAMADA_SQL = re.compile(r"\b(?P<funcion>(?:public|private)\.[a-z][a-z0-9_]*)\(")
LLAMADA_REST = re.compile(r"/rest/v1/rpc/(?P<funcion>[a-z][a-z0-9_]*)")
# El cliente de FastAPI parte la llamada en varias líneas, con el nombre en la
# siguiente: sin admitir el espacio, ninguna de sus RPC entraría en el recuento.
LLAMADA_CLIENTE = re.compile(r"""rpc\(\s*["'](?P<funcion>[a-z][a-z0-9_]*)["']""")
# El SQL escribe `timestamptz` y el catálogo `timestamp with time zone`. Son los
# alias que usa este repositorio; uno nuevo se delata solo, porque la firma
# normalizada dejará de coincidir con el manifiesto.
ALIAS_DE_TIPO = {
    "bool": "boolean",
    "int": "integer",
    "int4": "integer",
    "int8": "bigint",
    "timestamptz": "timestamp with time zone",
    "varchar": "character varying",
}


def firmas_declaradas() -> list[str]:
    lineas = MANIFEST.read_text("utf-8").splitlines()
    return [linea for linea in lineas if linea.strip() and not linea.startswith("#")]


def bloque_de_parametros(sql: str, apertura: int) -> str:
    """Devuelve el texto entre el paréntesis de apertura y su pareja."""
    profundidad = 0
    contenido = ""
    for caracter in sql[apertura:]:
        if caracter == "(":
            profundidad += 1
            if profundidad == 1:
                continue
        elif caracter == ")":
            profundidad -= 1
            if profundidad == 0:
                break
        if profundidad >= 1:
            contenido += caracter
    return contenido


def parametros(bloque: str) -> list[str]:
    profundidad = 0
    actual = ""
    partes: list[str] = []
    for caracter in bloque:
        if caracter == "(":
            profundidad += 1
        elif caracter == ")":
            profundidad -= 1
        elif caracter == "," and profundidad == 0:
            partes.append(actual)
            actual = ""
            continue
        actual += caracter
    if actual.strip():
        partes.append(actual)
    return partes


def normaliza(parametro: str) -> str:
    """`p_dry_run boolean DEFAULT true` -> `p_dry_run boolean`."""
    sin_default = re.split(r"\bDEFAULT\b", parametro, flags=re.IGNORECASE)[0]
    limpio = " ".join(sin_default.split())
    if not limpio:
        return ""
    nombre, _, tipo = limpio.partition(" ")
    tipo = tipo.strip().lower()
    return f"{nombre} {ALIAS_DE_TIPO.get(tipo, tipo)}"


def firmas_por_migracion(funcion: str) -> list[set[str]]:
    """Firmas declaradas para `funcion`, una entrada por migración que la declara."""
    declaraciones: list[set[str]] = []
    for migracion in MIGRATIONS:
        sql = migracion.read_text("utf-8")
        firmas = {
            "{}({})".format(
                funcion,
                ", ".join(
                    filter(
                        None,
                        (
                            normaliza(parametro)
                            for parametro in parametros(
                                bloque_de_parametros(sql, coincidencia.end() - 1)
                            )
                        ),
                    )
                ),
            )
            for coincidencia in DECLARACION.finditer(sql)
            if coincidencia.group("funcion").lower() == funcion
        }
        if firmas:
            declaraciones.append(firmas)
    return declaraciones


def test_el_manifiesto_declara_firmas_bien_formadas() -> None:
    firmas = firmas_declaradas()

    assert firmas, "el manifiesto está vacío"
    assert len(firmas) == len(set(firmas)), "hay firmas repetidas"
    for firma in firmas:
        assert re.fullmatch(r"(public|private)\.[a-z][a-z0-9_]*\(.*\)", firma), (
            f"firma mal formada: {firma}"
        )


def test_cada_firma_declarada_existe_en_las_migraciones() -> None:
    """Cambiar una firma en el SQL obliga a actualizar el manifiesto.

    Sin esto, editar una migración aplicada volvería a pasar inadvertido: el
    manifiesto seguiría describiendo la redacción vieja, coincidiría con una
    producción igual de vieja y el guardián nocturno saldría verde.
    """
    for firma in firmas_declaradas():
        funcion = firma.partition("(")[0]
        declaradas = firmas_por_migracion(funcion)

        assert declaradas, f"{funcion} no se declara en ninguna migración"
        assert firma in set().union(*declaradas), (
            f"el manifiesto declara `{firma}` y ninguna migración la declara así"
        )


def test_la_ultima_declaracion_de_cada_funcion_esta_en_el_manifiesto() -> None:
    """El test anterior mira el SQL entero, y ahí sobreviven redacciones viejas.

    Sin esta segunda dirección, una migración nueva que cambie la firma dejaría
    pasar el manifiesto obsoleto: la redacción anterior sigue en su fichero.
    """
    declaradas = set(firmas_declaradas())
    funciones = {firma.partition("(")[0] for firma in declaradas}

    for funcion in sorted(funciones):
        ultima = firmas_por_migracion(funcion)[-1]

        assert ultima <= declaradas, (
            f"la última migración declara {sorted(ultima - declaradas)} "
            f"y el manifiesto no lo recoge"
        )


def test_el_manifiesto_cubre_lo_que_invoca_produccion() -> None:
    declaradas = {firma.split("(", 1)[0] for firma in firmas_declaradas()}

    for consumidor in CONSUMIDORES:
        texto = consumidor.read_text("utf-8")
        invocadas = {coincidencia.group("funcion") for coincidencia in LLAMADA_SQL.finditer(texto)}
        for patron in (LLAMADA_REST, LLAMADA_CLIENTE):
            invocadas |= {
                f"public.{coincidencia.group('funcion')}" for coincidencia in patron.finditer(texto)
            }
        for funcion in sorted(invocadas):
            assert funcion in declaradas, (
                f"{consumidor.name} invoca {funcion} y el manifiesto no la declara"
            )


def test_el_guardian_no_reconcilia_ni_ejecuta_el_entorno() -> None:
    guardian = (BACKUP_DIR / "check-database-contract.sh").read_text("utf-8")

    assert "read_env_var_or_current" in guardian
    assert 'source "$ENV_FILE"' not in guardian
    assert "CREATE " not in guardian.upper().replace("CREATE OR REPLACE", "")
    assert "ALTER " not in guardian
    assert "DROP " not in guardian


def test_el_check_de_frescura_invoca_al_guardian_del_contrato() -> None:
    frescura = (BACKUP_DIR / "check-backup-freshness.sh").read_text("utf-8")

    assert "check-database-contract.sh" in frescura
    assert "La base de datos ya no coincide con el repositorio" in frescura
