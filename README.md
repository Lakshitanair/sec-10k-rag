# SEC 10-K RAG: Cited Q&A over Annual Reports

## Goal

A web app preloaded with the 10-K filings of five big tech companies, where a user asks a question and gets an answer that cites the exact company, year, and section, or says "not found" when the filings don't contain the answer.

## Why this project

Annual reports run 100-300 pages. Keyword search finds mentions but not answers, and a plain chatbot answers from memory and can state wrong figures with full confidence. This system answers only from the filings, shows its sources, refuses when it can't support an answer, and is evaluated on a hand-written test set.

## Scope

**Companies (target):** Apple, Microsoft, Alphabet, Amazon, and Meta or Nvidia. The pipeline is built on Apple first, and the others are added once it works end to end.

**Filings in scope (Apple):**

| Fiscal year | Filed | Fiscal year-end | Accession number |
|---|---|---|---|
| FY2025 | 2025-10-31 | 2025-09-27 | 0000320193-25-000079 |
| FY2024 | 2024-11-01 | 2024-09-28 | 0000320193-24-000123 |
| FY2023 | 2023-11-03 | 2023-09-30 | 0000320193-23-000106 |

Other companies' filings will be added here as they are chosen.

**Question types the system must handle:**

| Type | Example | "Correct" means |
|---|---|---|
| Factual lookup | What are Apple's main product categories? | Matches the filing text |
| Numeric / table | What was total net sales in fiscal 2024? | Exact figure, right year |
| Risk summary | What supply chain risks does Apple list? | Covers the main points, nothing invented |
| Year-over-year | How did the risk factors change from last year? | Real differences, both years cited |
| Cross-company | Which companies mention reliance on a single supplier? | Correct companies, each cited |
| Unanswerable | What is the CEO's favorite color? | Says "not found in the filings" |

## Out of scope

- 10-Q, 8-K, and other filing types (10-K only)
- Real-time or live market data
- User-uploaded documents
- Chat memory and user accounts

## Tools

Python, EDGAR's public JSON API, BeautifulSoup, sentence-transformers, a vector store (Chroma or FAISS), BM25, a reranker, an LLM via API, and Streamlit.

## Status

Setup complete. Filing lister working. Ingestion (downloading and parsing filings) is next.