import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw")
EVAL_DIR = Path("eval")

# Strings that must appear in the cited filing's original HTML text.
CHECKS = {
    "num-001": ["416,161"],
    "num-002": ["112,010"],
    "num-003": ["359,241"],
    "num-004": ["7.46"],
    "num-005": ["26,844"],
    "num-006": ["15,004,697"],
    "num-007": ["64,377"],
    "yoy-001": ["31,370", "34,550"],
    "yoy-002": ["64,377", "66,952"],
    "lookup-001": ["last Saturday of September"],
    "text-001": ["Ben Borders", "Kevan Parekh"],
    "text-002": ["Kevan Parekh"],
    "text-003": ["2023-09", "fourth quarter of 2026", "prospective"],
    "text-004": ["523 million", "between 2026 and 2027"],
    "lookup-002": ["September 27, 2019"],
}

# Unanswerable questions already confirmed by hand (Select-String searches
# for "2026", and reading Items 10 to 13, which point to the proxy statement).
MANUAL_VERIFIED = {"unans-001", "unans-003"}

_cache = {}


def filing_texts(ticker, fiscal_year):
    """Plain text of the original filing, in two variants."""
    key = (ticker, fiscal_year)
    if key not in _cache:
        matches = list(RAW_DIR.glob(f"{ticker}/FY{fiscal_year}_*.htm"))
        if not matches:
            _cache[key] = None
        else:
            html = matches[0].read_bytes().decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            variants = []
            for sep in (" ", ""):
                text = soup.get_text(sep).replace("\xa0", " ")
                variants.append(re.sub(r"\s+", " ", text))
            _cache[key] = variants
    return _cache[key]


def found(needle, variants):
    return any(needle in text for text in variants)


def main(write):
    for path in sorted(EVAL_DIR.glob("questions*.json")):
        questions = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for q in questions:
            qid = q["id"]
            if not q["answerable"]:
                if qid in MANUAL_VERIFIED:
                    print(f"MANUAL  {qid}")
                    if not q["verified"]:
                        q["verified"], changed = True, True
                else:
                    print(f"TODO    {qid}: unanswerable, not yet confirmed")
                continue
            needles = CHECKS.get(qid)
            if needles is None:
                print(f"SKIP    {qid}: no checks defined")
                continue
            src = q["sources"][0]
            variants = filing_texts(src["ticker"], src["fiscal_year"])
            if variants is None:
                print(f"NOFILE  {qid}: filing not found")
                continue
            missing = [n for n in needles if not found(n, variants)]
            if missing:
                print(f"FAIL    {qid}: not found in filing: {missing}")
            else:
                print(f"PASS    {qid}")
                if not q["verified"]:
                    q["verified"], changed = True, True
        if changed and write:
            path.write_text(
                json.dumps(questions, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"-> updated {path}")


if __name__ == "__main__":
    main(write="--write" in sys.argv)