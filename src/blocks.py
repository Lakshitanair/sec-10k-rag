import json
import re
from pathlib import Path

PROCESSED_DIR = Path("data/processed")

MAX_CONTEXT_LINES = 3    # lines above a table that may describe it
MAX_CONTEXT_CHARS = 250  # a longer line is a paragraph, not a title or unit note


def is_row(line: str) -> bool:
    """A table row has cells separated by ' | '."""
    return " | " in line


def is_group_label(line: str) -> bool:
    """A short line like 'Net sales:' that names the rows below it."""
    return len(line) <= 100 and line.endswith(":") and not is_row(line)


def find_tables(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start, end) line ranges of tables. end is exclusive."""
    runs = []
    i = 0
    while i < len(lines):
        if not is_row(lines[i]):
            i += 1
            continue
        start, end, j = i, i + 1, i + 1
        while j < len(lines):
            if is_row(lines[j]):
                j += 1
                end = j
            elif is_group_label(lines[j]) and j + 1 < len(lines) and is_row(lines[j + 1]):
                j += 1  # the label stays inside the table
            else:
                break
        if sum(is_row(line) for line in lines[start:end]) >= 2:
            runs.append((start, end))
        i = end
    return runs


def context_start(lines: list[str], table_start: int, floor: int) -> int:
    """Walk upward from a table to claim its title, unit note and intro sentence."""
    k = table_start
    while (
        k > floor
        and table_start - k < MAX_CONTEXT_LINES
        and len(lines[k - 1]) <= MAX_CONTEXT_CHARS
        and not is_row(lines[k - 1])
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
        if chunk:
            body = "\n".join(chunk)
            blocks.append({"kind": "text", "text": body, "n_chars": len(body)})

    for start, end in find_tables(lines):
        first = context_start(lines, start, cursor)
        add_text(lines[cursor:first])
        body = "\n".join(lines[first:end])
        blocks.append(
            {
                "kind": "table",
                "context": lines[first:start],
                "rows": lines[start:end],
                "text": body,
                "n_rows": sum(is_row(line) for line in lines[start:end]),
                "n_chars": len(body),
            }
        )
        cursor = end
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
        for item, block in sorted(tables, key=lambda t: -t[1]["n_rows"])[:4]:
            label = (block["context"] or block["rows"])[0][:60]
            print(f"    Item {item:<3} {block['n_rows']:>3} rows  {label}")


if __name__ == "__main__":
    process_all()