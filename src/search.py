import json
import re
import sys

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from src.chunk import INDEX_DIR
from src.index import MODEL_NAME, embed_text

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RRF_K = 60


def tokenize(text):
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*", text.lower())


class Searcher:
    def __init__(self):
        self.chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
        self.emb = np.load(INDEX_DIR / "embeddings.npy")
        self.model = SentenceTransformer(MODEL_NAME)
        self.bm25 = BM25Okapi([tokenize(embed_text(c)) for c in self.chunks])

    def dense(self, query, k=20):
        q = self.model.encode(QUERY_PREFIX + query, normalize_embeddings=True)
        scores = self.emb @ q
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]

    def keyword(self, query, k=20):
        scores = self.bm25.get_scores(tokenize(query))
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]

    def hybrid(self, query, k=20):
        fused = {}
        for results in (self.dense(query, 50), self.keyword(query, 50)):
            for rank, (i, _) in enumerate(results):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return [(i, s) for i, s in top]


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What were Apple's total net sales in fiscal 2025?"
    searcher = Searcher()
    for rank, (i, score) in enumerate(searcher.hybrid(query, 5), start=1):
        c = searcher.chunks[i]
        print(f"{rank}. FY{c['fiscal_year']} Item {c['item']} ({c['kind']}) score={score:.4f}")
        print("   " + c["text"][:200].replace("\n", " "))