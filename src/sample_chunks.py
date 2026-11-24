import json
import random

from src.chunk import INDEX_DIR

N = 12
SEED = 7


def main():
    chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    pool = [c for c in chunks if c["n_chars"] >= 300 and c["item"] != "front"]
    random.seed(SEED)
    lines = []
    for c in random.sample(pool, N):
        lines.append("=" * 70)
        lines.append(f"{c['id']} | FY{c['fiscal_year']} | Item {c['item']} | {c['kind']}")
        lines.append(c["text"])
        lines.append("")
    out = "scratch/sample.txt"
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print("wrote", out)


if __name__ == "__main__":
    main()