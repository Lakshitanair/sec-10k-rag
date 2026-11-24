"""Turn the section/block files into search-sized chunks."""
import json
import re
from pathlib import Path

from src.parse import TABLE_CLOSE, TABLE_OPEN

PROCESSED_DIR = Path("data/processed")
INDEX_DIR = PROCESSED_DIR / "index"

COMPANY_NAMES = {"AAPL": "Apple"}
SKIP_ITEMS = {"15"}  # exhibit index: long and low value
TEXT_MAX_CHARS = 1200
TABLE_MAX_CHARS = 2000
TABLE_HEADER_LINES = 4


def pack(units, max_chars):
    """Greedily join units into chunks, carrying one short unit over as overlap."""
    chunks, current, size = [], [], 0
    for unit in units:
        if current and size + len(unit) + 1 > max_chars:
            chunks.append("\n".join(current))
            last = current[-1]
            current, size = ([last], len(last)) if len(last) < 300 else ([], 0)
        current.append(unit)
        size += len(unit) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def split_text(text):
    units = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) <= TEXT_MAX_CHARS:
            units.append(para)
        else:
            units.extend(s for s in re.split(r"(?<=[.!?])\s+", para) if s)
    return pack(units, TEXT_MAX_CHARS)


def split_table(text):
    for marker in (TABLE_OPEN, TABLE_CLOSE):
        text = text.replace(marker, "")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if len("\n".join(lines)) <= TABLE_MAX_CHARS:
        return ["\n".join(lines)]
    header, body = lines[:TABLE_HEADER_LINES], lines[TABLE_HEADER_LINES:]
    header_size = sum(len(ln) + 1 for ln in header)
    chunks, current, size = [], [], header_size
    for line in body:
        if current and size + len(line) + 1 > TABLE_MAX_CHARS:
            chunks.append("\n".join(header + current))
            current, size = [], header_size
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(header + current))
    return chunks


def table_text(block):
    text = block["text"]
    ctx = block.get("context") or ""
    if isinstance(ctx, list):
        ctx = "\n".join(ctx)
    ctx = ctx.strip()
    if ctx and ctx not in text:
        text = ctx + "\n" + text
    return text


def make_header(ticker, fiscal_year, sec):
    name = COMPANY_NAMES.get(ticker, ticker)
    if sec["item"] == "front":
        where = "cover page"
    else:
        where = f"Item {sec['item']}, {sec.get('title', '')}".rstrip(", ")
    return f"{name} ({ticker}), fiscal {fiscal_year} Form 10-K, {where}"


def build_chunks():
    chunks = []
    for path in sorted(PROCESSED_DIR.glob("*/FY*.blocks.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        ticker, fiscal_year = doc["ticker"], int(doc["fiscal_year"])
        n = 0
        for sec in doc["sections"]:
            if sec["item"] in SKIP_ITEMS:
                continue
            if "blocks" not in sec:
                raise SystemExit(f"No 'blocks' key in a section. Keys found: {list(sec.keys())}")
            header = make_header(ticker, fiscal_year, sec)
            for block in sec["blocks"]:
                if block["kind"] == "table":
                    pieces = split_table(table_text(block))
                else:
                    pieces = split_text(block["text"])
                for piece in pieces:
                    if not piece.strip():
                        continue
                    n += 1
                    chunks.append({
                        "id": f"{ticker}-FY{fiscal_year}-{n:04d}",
                        "ticker": ticker,
                        "fiscal_year": fiscal_year,
                        "accession_number": doc.get("accession_number"),
                        "item": sec["item"],
                        "section_title": sec.get("title", ""),
                        "kind": block["kind"],
                        "header": header,
                        "text": piece,
                        "n_chars": len(piece),
                    })
    return chunks


def main():
    chunks = build_chunks()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    (INDEX_DIR / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False), encoding="utf-8"
    )
    print(len(chunks), "chunks")
    for fy in sorted({c["fiscal_year"] for c in chunks}):
        sub = [c for c in chunks if c["fiscal_year"] == fy]
        tables = sum(1 for c in sub if c["kind"] == "table")
        print(f"FY{fy}: {len(sub)} chunks ({tables} from tables)")
    sizes = sorted(c["n_chars"] for c in chunks)
    print("chars: min", sizes[0], "| median", sizes[len(sizes) // 2], "| max", sizes[-1])
    sample = next(
        (c for c in chunks
         if c["kind"] == "table" and c["fiscal_year"] == 2025
         and c["item"] == "8" and "Total net sales" in c["text"]),
        None,
    )
    if sample:
        print("\n--- sample table chunk ---")
        print(sample["header"])
        print(sample["text"])


if __name__ == "__main__":
    main()