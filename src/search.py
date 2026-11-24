import json
import re
import sys

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from src.chunk import INDEX_DIR
from src.index import MODEL_NAME, embed_text

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RRF_K = 60
YEAR_RE = re.compile(r"\b(20[12]\d)\b(?!-\d)")


def tokenize(text):
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*", text.lower())


class Searcher:
    def __init__(self):
        self.chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
        self.emb = np.load(INDEX_DIR / "embeddings.npy")
        self.years = np.array([c["fiscal_year"] for c in self.chunks])
        self.model = SentenceTransformer(MODEL_NAME)
        self.bm25 = BM25Okapi([tokenize(embed_text(c)) for c in self.chunks])
        self.reranker = None

    def detect_year(self, query):
        """Latest year mentioned in the question, if we have that filing."""
        mentioned = [int(y) for y in YEAR_RE.findall(query)]
        if mentioned and max(mentioned) in set(self.years.tolist()):
            return max(mentioned)
        return None

    def _top(self, scores, k, year):
        if year is not None:
            scores = np.where(self.years == year, scores, -np.inf)
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top if np.isfinite(scores[i])]

    def dense(self, query, k=20, year=None):
        q = self.model.encode(QUERY_PREFIX + query, normalize_embeddings=True)
        return self._top(self.emb @ q, k, year)

    def keyword(self, query, k=20, year=None):
        return self._top(self.bm25.get_scores(tokenize(query)), k, year)

    def hybrid(self, query, k=20, year=None):
        fused = {}
        for results in (self.dense(query, 50, year), self.keyword(query, 50, year)):
            for rank, (i, _) in enumerate(results):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return [(i, s) for i, s in top]

    def rerank(self, query, results, k=20):
        if self.reranker is None:
            self.reranker = CrossEncoder(RERANK_MODEL)
        pairs = [(query, embed_text(self.chunks[i])) for i, _ in results]
        scores = self.reranker.predict(pairs)
        order = np.argsort(-scores)[:k]
        return [(results[j][0], float(scores[j])) for j in order]


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What were Apple's total net sales in fiscal 2025?"
    searcher = Searcher()
    year = searcher.detect_year(query)
    print("year filter:", year)
    candidates = searcher.hybrid(query, 30, year)
    for rank, (i, score) in enumerate(searcher.rerank(query, candidates, 5), start=1):
        c = searcher.chunks[i]
        print(f"{rank}. FY{c['fiscal_year']} Item {c['item']} ({c['kind']}) score={score:.3f}")
        print("   " + c["text"][:200].replace("\n", " "))