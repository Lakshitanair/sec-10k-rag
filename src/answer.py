import re
import sys

from src.llm import generate
from src.search import Searcher
from src import llm

TOP_K = 5
NOT_FOUND = "NOT_FOUND"

SYSTEM = """You answer questions about company annual reports (SEC Form 10-K) using ONLY the numbered passages provided.

Rules:
- Use only facts stated in the passages. Never use outside knowledge.
- Cite every claim with the passage number in square brackets, like [1] or [2][3].
- Check the company, fiscal year, units (millions, thousands, or per-share dollars) and which table row a number belongs to before answering.
- If the passages do not contain the answer, reply with exactly: NOT_FOUND
- If the question is about a company or year the passages do not cover, reply with exactly: NOT_FOUND
- Be concise: 1 to 3 sentences."""


def format_passages(chunks):
    blocks = []
    for n, c in enumerate(chunks, start=1):
        blocks.append(f"[{n}] ({c['header']})\n{c['text']}")
    return "\n\n".join(blocks)


def answer_question(searcher, question, top_k=TOP_K):
    year = searcher.detect_year(question)
    hits = searcher.hybrid(question, top_k, year=year)
    chunks = [searcher.chunks[i] for i, _ in hits]
    user = f"Passages:\n\n{format_passages(chunks)}\n\nQuestion: {question}"
    text = generate(SYSTEM, user)
    refused = NOT_FOUND in text.upper()
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 1 <= int(n) <= len(chunks)})
    return {
        "question": question,
        "answer": text,
        "refused": refused,
        "year_filter": year,
        "cited": [chunks[n - 1]["id"] for n in cited],
        "retrieved": [c["id"] for c in chunks],
    }


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What were Apple's total net sales in fiscal 2025?"
    result = answer_question(Searcher(), question)
    print("year filter:", result["year_filter"])
    print("model:", llm.LAST_MODEL)
    print("answer:", result["answer"])
    print("cited chunks:", result["cited"])