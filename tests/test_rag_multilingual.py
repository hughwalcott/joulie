"""Retriever routing (JTBD-03): English stays on the shipped collection; a
language the multilingual index covers is searched there, as asked, against its
own distance threshold. Built with __new__ so no model or ChromaDB is loaded."""

from joulie import config
from joulie.rag import Retriever


class FakeModel:
    def __init__(self, name):
        self.name = name

    def encode(self, texts, convert_to_numpy=True):
        import numpy as np
        return np.zeros((len(texts), 3))


class FakeCollection:
    def __init__(self, name, distance):
        self.name, self.distance, self.queries = name, distance, 0

    def count(self):
        return 1

    def query(self, query_embeddings, n_results):
        self.queries += 1
        return {"documents": [[f"from {self.name}"]],
                "metadatas": [[{"publisher_short": "EECA"}]],
                "distances": [[self.distance]]}


def make(ml=True, en_distance=0.3, ml_distance=0.3):
    r = Retriever.__new__(Retriever)
    r.embed_model, r.collection = FakeModel("en"), FakeCollection("en", en_distance)
    r.ml_model = FakeModel("ml") if ml else None
    r.ml_collection = FakeCollection("ml", ml_distance) if ml else None
    r.top_k, r.distance_threshold = 3, config.RAG_DISTANCE_THRESHOLD
    return r


class TestRouting:
    def test_english_uses_the_shipped_collection(self):
        r = make()
        assert r.retrieve("heat pumps?")[0]["text"] == "from en"
        assert r.ml_collection.queries == 0

    def test_hindi_mandarin_and_european_languages_are_searched_as_asked(self):
        r = make()
        for lang in ("hi", "zh", "de", "fr", "es", "pl", "hu", "tr"):
            assert r.handles(lang), lang
            assert r.retrieve("q", lang=lang)[0]["text"] == "from ml"

    def test_te_reo_is_not_covered_so_it_falls_back_to_translation(self):
        assert not make().handles("mi")

    def test_without_the_index_nothing_non_english_is_covered(self):
        r = make(ml=False)
        assert not r.handles("zh")
        assert r.retrieve("q", lang="zh")[0]["text"] == "from en"

    def test_the_multilingual_threshold_applies_to_multilingual_results(self, monkeypatch):
        monkeypatch.setattr(config, "RAG_MULTILINGUAL_DISTANCE_THRESHOLD", 0.55)
        # 0.6 would pass the English threshold (0.7) but is off-topic on the
        # multilingual model's scale.
        assert make(ml_distance=0.6).retrieve("q", lang="zh") == []
