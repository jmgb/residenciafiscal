"""Contrato del descargador: qué normas se piden y qué le pasa al manifiesto.

Nada aquí toca la red. Lo que se comprueba es la parte que decide, que es donde
se puede perder una norma sin que nadie lo note: la tabla de convenios que el
índice del BOE no devuelve y la fusión del manifiesto cuando se descarga una
sola norma.
"""

from __future__ import annotations

import json
from pathlib import Path

from descargar_normativa import (
    CDI_DEROGADO,
    CDI_NO_CONSOLIDADO,
    NUCLEO,
    RECLASIFICACION,
    cdis_del_indice,
    desapariciones_no_declaradas,
    fusionar_manifiesto,
    grupo_declarado,
    grupo_del_indice,
    normas_del_diario,
)

MANIFIESTO = Path(__file__).parents[1] / "normativa" / "es" / "manifest.json"


def test_los_convenios_no_consolidados_son_vigentes_y_salen_del_diario() -> None:
    del_diario = normas_del_diario()

    for boe_id in CDI_NO_CONSOLIDADO:
        grupo, motivo = del_diario[boe_id]
        # `cdi`, no `cdi_derogado`: están en vigor. Confundirlos publicaría el
        # convenio con el rótulo de norma derogada.
        assert grupo == "cdi", boe_id
        assert motivo, f"{boe_id} no explica por qué no está en el índice"

    # Y no se solapan con los convenios sustituidos, que sí están derogados.
    assert not set(CDI_NO_CONSOLIDADO) & set(CDI_DEROGADO)


def test_el_grupo_se_deduce_de_las_tablas_declaradas() -> None:
    assert grupo_declarado(NUCLEO[0]) == ("nucleo", "")
    assert grupo_declarado("BOE-A-2004-11070") == ("cdi", CDI_NO_CONSOLIDADO["BOE-A-2004-11070"])
    assert grupo_declarado("BOE-A-1976-23347") == (
        "cdi_derogado",
        CDI_DEROGADO["BOE-A-1976-23347"],
    )
    # Un convenio cualquiera del índice no está declarado en ninguna tabla: se
    # pide a la base consolidada.
    assert grupo_declarado("BOE-A-1997-12729") is None


def test_un_convenio_declarado_a_mano_no_se_descarga_dos_veces() -> None:
    """El BOE puede acabar consolidando lo que hoy solo está en el diario."""
    paraguay = "BOE-A-2024-15573"
    indice = [
        ("BOE-A-1997-12729", "Convenio … para evitar la doble imposición … República Francesa"),
        (paraguay, "Convenio … para evitar la doble imposición … República del Paraguay"),
        ("BOE-A-2000-0000", "Ley de cualquier otra cosa"),
    ]

    consolidadas, ya_consolidados = cdis_del_indice(indice)

    # Sigue bajándose del diario mientras esté declarado, y no por duplicado.
    assert consolidadas == ["BOE-A-1997-12729"]
    # Pero el aviso pide retirarlo de la tabla, que es la acción correcta.
    assert ya_consolidados == [paraguay]


def test_descargar_una_norma_no_borra_el_inventario_de_las_demas() -> None:
    previo = {"normas": [{"id": "BOE-A-1", "grupo": "cdi"}, {"id": "BOE-A-2", "grupo": "cdi"}]}
    nuevos: list[dict[str, object]] = [
        {"id": "BOE-A-2", "grupo": "cdi", "texto_sha256": "nuevo"},
        {"id": "BOE-A-3"},
    ]

    fusionado = fusionar_manifiesto(previo, nuevos)

    assert [registro["id"] for registro in fusionado] == ["BOE-A-1", "BOE-A-2", "BOE-A-3"]
    # El registro repetido se sustituye por el recién descargado, no se duplica.
    assert fusionado[1]["texto_sha256"] == "nuevo"


def test_detecta_normas_que_desaparecen_en_una_descarga_completa() -> None:
    previo = {
        "normas": [
            {"id": "BOE-A-1", "grupo": "cdi"},
            {"id": "BOE-A-2", "grupo": "cdi"},
        ]
    }
    nuevos: list[dict[str, object]] = [{"id": "BOE-A-1", "grupo": "cdi"}]

    assert desapariciones_no_declaradas(previo, nuevos) == ["BOE-A-2"]


def test_permite_baja_explicita_al_comparar_manifiestos() -> None:
    previo = {"normas": [{"id": "BOE-A-1", "grupo": "cdi"}]}
    nuevos: list[dict[str, object]] = []

    assert desapariciones_no_declaradas(previo, nuevos, bajas={"BOE-A-1"}) == []


def test_el_filtro_por_titulo_arrastra_normas_que_no_son_un_cdi_general() -> None:
    """`doble imposición` en el título no basta para ser un convenio de renta.

    El índice devuelve una ley interna sobre doble imposición intersocietaria y
    dos convenios sectoriales de navegación marítima y aérea. Los tres carecen
    de regla de residencia, y publicarlos como CDI del país haría que la
    relación bilateral de Venezuela apuntase a un convenio de navegación.
    """
    assert grupo_del_indice("BOE-A-1997-12729") == ("cdi", "")

    for boe_id, (grupo, motivo) in RECLASIFICACION.items():
        assert grupo_del_indice(boe_id) == (grupo, motivo)
        assert grupo != "cdi", boe_id
        assert motivo, f"{boe_id} no explica por qué se reclasifica"


def test_el_manifiesto_publicado_refleja_la_reclasificacion() -> None:
    """El manifiesto versionado ya trae lo que produciría una descarga nueva.

    Sin esta comprobación, la próxima ejecución con red devolvería las tres
    normas al grupo `cdi` y nadie se enteraría hasta ver un convenio de
    navegación publicado como CDI.
    """
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    registros = {registro["id"]: registro for registro in manifiesto["normas"]}

    for boe_id, (grupo, _) in RECLASIFICACION.items():
        assert registros[boe_id]["grupo"] == grupo, boe_id


def test_las_reclasificadas_son_las_que_no_publican_articulo_de_residencia() -> None:
    """Dos tablas describen el mismo hecho y no pueden divergir."""
    from export_normativa import SIN_PRECEPTO_RESIDENCIA

    assert set(RECLASIFICACION) == set(SIN_PRECEPTO_RESIDENCIA)


def test_el_manifiesto_publicado_incluye_los_dos_convenios_no_consolidados() -> None:
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    registros = {registro["id"]: registro for registro in manifiesto["normas"]}

    for boe_id in CDI_NO_CONSOLIDADO:
        assert boe_id in registros, f"{boe_id} no se ha descargado"
        assert registros[boe_id]["grupo"] == "cdi"
        assert registros[boe_id]["fuente"] == "diario"
