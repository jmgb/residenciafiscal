"""El runtime futuro FastAPI debe usar el mismo rollout que producción."""

from pathlib import Path


def test_defaults_del_runtime_apuntan_al_rollout_de_106() -> None:
    from api.chat_runtime import DEFAULT_CORPUS, DEFAULT_STORE_STATE
    from jurisprudence_retrieval_corpus import load_retrieval_corpus

    corpus = load_retrieval_corpus(DEFAULT_CORPUS.read_bytes())

    assert DEFAULT_CORPUS.name == "rollout-106.corpus.json"
    assert DEFAULT_STORE_STATE.name == "rollout-106-store.json"
    assert len(corpus.sources) == 106
    assert len(corpus.units) == 74
    assert DEFAULT_CORPUS == (
        Path(__file__).resolve().parents[1]
        / "knowledge/jurisprudencia-v3/retrieval/rollout-106.corpus.json"
    )
