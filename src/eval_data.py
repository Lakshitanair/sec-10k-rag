import json
from pathlib import Path

EVAL_DIR = Path("eval")


def load_questions():
    questions = []
    for path in sorted(EVAL_DIR.glob("questions*.json")):
        questions.extend(json.loads(path.read_text(encoding="utf-8")))
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "duplicate question ids"
    return questions


if __name__ == "__main__":
    qs = load_questions()
    print(len(qs), "questions")
    print(sum(1 for q in qs if not q["answerable"]), "unanswerable")