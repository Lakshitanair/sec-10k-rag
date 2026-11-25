import json
from pathlib import Path

from src import llm
from src.answer import answer_question
from src.eval_data import load_questions
from src.eval_retrieval import is_hit
from src.llm import generate
from src.search import Searcher
from src.verify_eval import CHECKS

OUT = Path("eval/results/answers_v1.json")

JUDGE_SYSTEM = """You grade answers to questions about 10-K filings.
You get a question, a reference answer, and a candidate answer.
Reply with exactly one word: CORRECT if the candidate states the same facts as the reference (same numbers, same units, same fiscal year; extra detail is fine), otherwise INCORRECT."""


def judge(q, answer):
    user = (f"Question: {q['question']}\nReference answer: {q['answer']}\n"
            f"Candidate answer: {answer}")
    reply = generate(JUDGE_SYSTEM, user).strip().upper()
    return reply.startswith("CORRECT")


def save(results):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


def summarize(label, qs, results, by_id):
    done = [q for q in qs if "answer" in results.get(q["id"], {})]
    pending = len(qs) - len(done)
    answerable = [q for q in done if q["answerable"]]
    unanswerable = [q for q in done if not q["answerable"]]
    print(f"\n=== {label} ({len(done)} done" + (f", {pending} pending, rerun to finish" if pending else "") + ") ===")
    if answerable:
        refused = [q for q in answerable if results[q["id"]]["refused"]]
        graded = [q for q in answerable if not results[q["id"]]["refused"]]
        correct = [q for q in graded if results[q["id"]].get("correct")]
        wrong = [q for q in graded if "correct" in results[q["id"]] and not results[q["id"]]["correct"]]
        cited_ok = [q for q in correct
                    if any(is_hit(by_id[c], q) for c in results[q["id"]]["cited"] if c in by_id)]
        n = len(answerable)
        print(f"Answerable ({n})")
        print(f"  correct answers:        {len(correct)}/{n}")
        print(f"  false refusals:         {len(refused)}/{n}")
        print(f"  wrong answers:          {len(wrong)}/{n}")
        if correct:
            print(f"  correct with valid citation: {len(cited_ok)}/{len(correct)}")
    if unanswerable:
        refused = [q for q in unanswerable if results[q["id"]]["refused"]]
        m = len(unanswerable)
        print(f"Unanswerable ({m})")
        print(f"  correctly refused:      {len(refused)}/{m}")
        print(f"  answered anyway:        {m - len(refused)}/{m}")


def main():
    results = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    searcher = Searcher()
    by_id = {c["id"]: c for c in searcher.chunks}
    questions = [q for q in load_questions()
                 if not q["answerable"] or q.get("check") or q["id"] in CHECKS]

    for q in questions:
        rec = results.get(q["id"], {})
        try:
            if "answer" not in rec:
                r = answer_question(searcher, q["question"])
                rec.update(answer=r["answer"], refused=r["refused"], cited=r["cited"],
                           retrieved=r["retrieved"], model=llm.LAST_MODEL)
            if q["answerable"] and not rec["refused"] and "correct" not in rec:
                rec["correct"] = judge(q, rec["answer"])
        except Exception as exc:  # keep going; rerun later fills the gaps
            print(f"{q['id']:<12} ERROR: {exc}")
            results[q["id"]] = rec
            save(results)
            continue
        results[q["id"]] = rec
        save(results)
        status = "refused" if rec["refused"] else ("correct" if rec.get("correct") else "WRONG")
        print(f"{q['id']:<12} {status:<8} model={rec['model']}")

    summarize("all", questions, results, by_id)
    summarize("tuned", [q for q in questions if q.get("set") != "heldout"], results, by_id)
    summarize("held-out", [q for q in questions if q.get("set") == "heldout"], results, by_id)
    print("\nsaved", OUT)


if __name__ == "__main__":
    main()