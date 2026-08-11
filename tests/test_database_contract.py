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
BAJA = re.compile(
    r"DROP\s+FUNCTION\s+(?:IF\s+EXISTS\s+)?(?P<funcion>(?:public|private)\.[a-z][a-z0-9_]*)\s*\(",
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


def lineas_del_manifiesto(tipo: str) -> list[str]:
    """Líneas de un tipo (`firma`, `restriccion`, `columna`), sin su prefijo."""
    return [
        linea[len(tipo) + 1 :]
        for linea in MANIFEST.read_text("utf-8").splitlines()
        if linea.startswith(f"{tipo} ")
    ]


def firmas_declaradas() -> list[str]:
    return lineas_del_manifiesto("firma")


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


def sin_valor_por_defecto(parametro: str) -> str:
    """`p_dry_run boolean DEFAULT true` -> `p_dry_run boolean`."""
    return " ".join(re.split(r"\bDEFAULT\b", parametro, flags=re.IGNORECASE)[0].split())


def normaliza(parametro: str) -> str:
    limpio = sin_valor_por_defecto(parametro)
    if not limpio:
        return ""
    nombre, _, tipo = limpio.partition(" ")
    return f"{nombre} {normaliza_tipo(tipo)}"


def normaliza_tipo(tipo: str) -> str:
    limpio = " ".join(tipo.split()).lower()
    return ALIAS_DE_TIPO.get(limpio, limpio)


def tipo_de(parametro: str, *, con_nombre: bool) -> str:
    """El tipo de un parámetro, esté declarado con nombre (`CREATE`) o sin él (`DROP`)."""
    limpio = sin_valor_por_defecto(parametro)
    if not limpio:
        return ""
    return normaliza_tipo(limpio.partition(" ")[2] if con_nombre else limpio)


def estado_declarado() -> dict[tuple[str, tuple[str, ...]], str]:
    """Reproduce, migración a migración, la firma que el repositorio deja viva.

    La clave es la que usa PostgreSQL para identificar una función: su nombre y
    los tipos de sus argumentos. `CREATE OR REPLACE` sustituye esa sobrecarga
    —también si solo cambian los nombres de parámetro— y `DROP FUNCTION` la
    retira. Comparar solo con la última migración que declara cada función daría
    por vivo lo que otra posterior dio de baja.
    """
    estado: dict[tuple[str, tuple[str, ...]], str] = {}
    for migracion in MIGRATIONS:
        sql = migracion.read_text("utf-8")
        for coincidencia in DECLARACION.finditer(sql):
            funcion = coincidencia.group("funcion").lower()
            declarados = parametros(bloque_de_parametros(sql, coincidencia.end() - 1))
            firmados = [normaliza(parametro) for parametro in declarados]
            vivos = [parametro for parametro in firmados if parametro]
            tipos = tuple(
                tipo for tipo in (tipo_de(p, con_nombre=True) for p in declarados) if tipo
            )
            estado[(funcion, tipos)] = "{}({})".format(funcion, ", ".join(vivos))
        for coincidencia in BAJA.finditer(sql):
            funcion = coincidencia.group("funcion").lower()
            retirados = parametros(bloque_de_parametros(sql, coincidencia.end() - 1))
            tipos = tuple(
                tipo for tipo in (tipo_de(p, con_nombre=False) for p in retirados) if tipo
            )
            estado.pop((funcion, tipos), None)
    return estado


def test_el_manifiesto_declara_lineas_bien_formadas() -> None:
    utiles = [
        linea
        for linea in MANIFEST.read_text("utf-8").splitlines()
        if linea.strip() and not linea.startswith("#")
    ]

    assert utiles, "el manifiesto está vacío"
    assert len(utiles) == len(set(utiles)), "hay líneas repetidas"
    for linea in utiles:
        assert linea.split(" ", 1)[0] in {"firma", "restriccion", "columna"}, (
            f"tipo de línea desconocido: {linea}"
        )
    for firma in firmas_declaradas():
        assert re.fullmatch(r"(public|private)\.[a-z][a-z0-9_]*\(.*\)", firma), (
            f"firma mal formada: {firma}"
        )
    for linea in lineas_del_manifiesto("restriccion") + lineas_del_manifiesto("columna"):
        assert re.match(r"(public|private)\.[a-z][a-z0-9_]* [a-z][a-z0-9_]* \S", linea), (
            f"línea mal formada: {linea}"
        )


def test_el_manifiesto_es_el_estado_que_declaran_las_migraciones() -> None:
    """El manifiesto y el SQL dicen lo mismo, firma a firma y en las dos direcciones.

    Sobra una: el manifiesto describe una redacción que ya no está en el SQL, y
    entonces coincidiría con una producción igual de vieja mientras el guardián
    nocturno sale verde. Falta una: alguien cambió o añadió una firma sin tocar
    el manifiesto, y esa función se quedaría sin vigilar.
    """
    declarado = set(estado_declarado().values())
    manifiesto = set(firmas_declaradas())

    assert not manifiesto - declarado, (
        f"el manifiesto declara firmas que el SQL no deja vivas: {sorted(manifiesto - declarado)}"
    )
    assert not declarado - manifiesto, (
        f"las migraciones dejan vivas firmas que el manifiesto no declara: "
        f"{sorted(declarado - manifiesto)}"
    )


def test_las_restricciones_y_columnas_declaradas_salen_de_alguna_migracion() -> None:
    """Estas dos se comprueban por nombre, no por definición, y es deliberado.

    La definición exacta la compara `check-database-contract.sh` contra el
    catálogo vivo, que ya la imprime normalizada. Reproducirla desde el SQL
    exigiría interpretar `ADD COLUMN ... DEFAULT ... CHECK (...)`, y ese parser
    sería más frágil que el hueco que cierra. Aquí basta con impedir que se
    declare algo que ninguna migración crea, que es como se cuela una errata.

    El límite, dicho claro: si una migración posterior retira la restricción o
    la columna, esto no lo ve, porque busca el nombre en todo el SQL. Lo canta
    el guardián contra producción en cuanto se aplique —«declarado y ausente en
    la base de datos»—, no CI.
    """
    sql = "\n".join(migracion.read_text("utf-8") for migracion in MIGRATIONS)

    for linea in lineas_del_manifiesto("restriccion") + lineas_del_manifiesto("columna"):
        tabla, nombre = linea.split(" ")[:2]

        assert tabla in sql, f"la tabla {tabla} no aparece en ninguna migración"
        assert nombre in sql, f"{nombre} no aparece en ninguna migración"


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
