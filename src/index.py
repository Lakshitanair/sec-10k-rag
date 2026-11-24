import json

import numpy as np
from sentence_transformers import SentenceTransformer

from src.chunk import INDEX_DIR

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MAX_TOKENS = 512


def embed_text(chunk):
    """What the model sees: the label plus the text."""
    return chunk["header"] + "\n" + chunk["text"]


def main():
    chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    texts = [embed_text(c) for c in chunks]
    model = SentenceTransformer(MODEL_NAME)
    model.max_seq_length = MAX_TOKENS

    lengths = [len(ids) for ids in model.tokenizer(texts, truncation=False)["input_ids"]]
    too_long = sum(1 for n in lengths if n > MAX_TOKENS)
    print(f"{too_long} of {len(texts)} chunks exceed {MAX_TOKENS} tokens (the model cuts them off)")

    emb = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True)
    np.save(INDEX_DIR / "embeddings.npy", emb)
    print("saved embeddings", emb.shape)


if __name__ == "__main__":
    main()