import json
from pathlib import Path

from src.parse import TABLE_CLOSE, TABLE_OPEN

PROCESSED_DIR = Path("data/processed")

MAX_CONTEXT_LINES = 3    # lines above a table that may describe it
MAX_CONTEXT_CHARS = 250  # a longer line is a paragraph, not a title or unit note


def find_tables(lines: list[str]) -> list[tuple[int, int]]:
    """Return (open_marker_index, close_marker_index) for each table.
    Tables that touch each other (nothing in between) are merged into one."""
    runs = []
    open_at = None
    for i, line in enumerate(lines):
        if line == TABLE_OPEN:
            open_at = i
        elif line == TABLE_CLOSE and open_at is not None:
            if i - open_at > 1:  # skip empty tables
                if runs and runs[-1][1] + 1 == open_at:
                    runs[-1] = (runs[-1][0], i)
                else:
                    runs.append((open_at, i))
            open_at = None
    return runs


def context_start(lines: list[str], table_start: int, floor: int) -> int:
    """Walk upward from a table to claim its title, unit note and intro sentence."""
    k = table_start
    while (
        k > floor
        and table_start - k < MAX_CONTEXT_LINES
        and len(lines[k - 1]) <= MAX_CONTEXT_CHARS
        and not lines[k - 1].startswith("See accompanying")  # belongs to the table above
    ):
        k -= 1
    return k


def build_blocks(text: str) -> list[dict]:
    """Split a section into text blocks and table blocks, in order."""
    if not text.strip():
        return []
    lines = text.split("\n")
    blocks = []
    cursor = 0  # first line not yet placed in a block

    def add_text(chunk: list[str]) -> None:
        chunk = [line for line in chunk if line not in (TABLE_OPEN, TABLE_CLOSE)]
        if chunk:
            body = "\n".join(chunk)
            blocks.append({"kind": "text", "text": body, "n_chars": len(body)})

    for open_at, close_at in find_tables(lines):
        first = context_start(lines, open_at, cursor)
        add_text(lines[cursor:first])
        context = lines[first:open_at]
        rows = [l for l in lines[open_at + 1 : close_at] if l not in (TABLE_OPEN, TABLE_CLOSE)]
        body = "\n".join(context + rows)
        blocks.append(
            {
                "kind": "table",
                "context": context,
                "rows": rows,
                "text": body,
                "n_rows": len(rows),
                "n_chars": len(body),
            }
        )
        cursor = close_at + 1
    add_text(lines[cursor:])
    return blocks


def process_all() -> None:
    for sections_path in sorted(PROCESSED_DIR.glob("*/*.sections.json")):
        record = json.loads(sections_path.read_text(encoding="utf-8"))
        for section in record["sections"]:
            section["blocks"] = build_blocks(section.pop("text"))

        out_path = sections_path.with_name(
            sections_path.name.replace(".sections.json", ".blocks.json")
        )
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        tables = [
            (section["item"], block)
            for section in record["sections"]
            for block in section["blocks"]
            if block["kind"] == "table"
        ]
        texts = [
            block
            for section in record["sections"]
            for block in section["blocks"]
            if block["kind"] == "text"
        ]
        table_chars = sum(block["n_chars"] for _, block in tables)
        text_chars = sum(block["n_chars"] for block in texts)
        print(f"{record['ticker']} FY{record['fiscal_year']}: "
              f"{len(texts)} text blocks ({text_chars:,} chars), "
              f"{len(tables)} tables ({table_chars:,} chars) -> {out_path}")
        print("  largest tables:")
        for item, block in sorted(tables, key=lambda t: -t[1]["n_rows"])[:5]:
            label = (block["context"] or block["rows"])[0][:60]
            print(f"    Item {item:<3} {block['n_rows']:>3} rows  {label}")


if __name__ == "__main__":
    process_all()