import json
import re
from pathlib import Path

from src.eval_data import load_questions
from src.search import Searcher
from src.verify_eval import CHECKS

KS = (1, 5, 10)
DEPTH = 20
RESULTS_DIR = Path("eval/results")


def norm(text):
    return re.sub(r"\s+", " ", text.replace("\xa0", " "))


def is_hit(chunk, question):
    needles = question.get("check") or CHECKS[question["id"]]
    text = norm(chunk["text"])
    for src in question["sources"]:
        if (chunk["ticker"] == src["ticker"]
                and int(chunk["fiscal_year"]) == int(src["fiscal_year"])
                and all(n in text for n in needles)):
            return True
    return False


def main():
    searcher = Searcher()
    questions = [q for q in load_questions()
                 if q["answerable"] and (q.get("check") or q["id"] in CHECKS)]

    def with_year(fn):
        return lambda q, k: fn(q, k, year=searcher.detect_year(q))

    methods = {
        "dense": searcher.dense,
        "keyword": searcher.keyword,
        "hybrid": searcher.hybrid,
        "dense+yr": with_year(searcher.dense),
        "hybrid+yr": with_year(searcher.hybrid),
        "hyb+yr+rank": lambda q, k: searcher.rerank(q, with_year(searcher.hybrid)(q, 30), k),
    }
    ranks = {name: {} for name in methods}

    for q in questions:
        for name, search in methods.items():
            rank = None
            for pos, (i, _) in enumerate(search(q["question"], DEPTH), start=1):
                if is_hit(searcher.chunks[i], q):
                    rank = pos
                    break
            ranks[name][q["id"]] = rank

    print("\nRank of first correct chunk ('-' = not in top %d)\n" % DEPTH)
    print(f"{'question':<12}" + "".join(f"{m:>13}" for m in methods))
    for q in questions:
        row = "".join(f"{(ranks[m][q['id']] or '-')!s:>13}" for m in methods)
        print(f"{q['id']:<12}{row}")

    n = len(questions)
    print(f"\nHit rate over {n} answerable questions")
    summary = {}
    for name in methods:
        summary[name] = {}
        parts = []
        for k in KS:
            hits = sum(1 for r in ranks[name].values() if r is not None and r <= k)
            summary[name][f"hit@{k}"] = round(hits / n, 3)
            parts.append(f"hit@{k} {hits}/{n}")
        print(f"{name:<13}" + "   ".join(parts))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "retrieval_v2.json"
    out.write_text(json.dumps({"summary": summary, "ranks": ranks}, indent=2), encoding="utf-8")
    print("\nsaved", out)


if __name__ == "__main__":
    main()