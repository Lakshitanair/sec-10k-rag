import json
import re
from pathlib import Path

PROCESSED_DIR = Path("data/processed")

# A real section heading looks like "Item 1A. Risk Factors": the item id, a
# period, and the title on the SAME line. Table-of-contents entries are just
# "Item 1A." alone on a line, so this pattern skips them.
HEADING_RE = re.compile(r"^Item\s+(\d{1,2}[A-C]?)\.\s+(?!\|)(\S.*)$", re.IGNORECASE)

# Items a 10-K normally has (older filings lack some, e.g. 1C)
EXPECTED_ITEMS = [
    "1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7", "7A", "8",
    "9", "9A", "9B", "9C", "10", "11", "12", "13", "14", "15", "16",
]


def split_sections(text: str) -> tuple[list[dict], list[str]]:
    """Split cleaned filing text into sections, one per Item."""
    lines = text.split("\n")

    # Find every line that looks like a real heading
    candidates: dict[str, list[tuple[int, str]]] = {}
    for i, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            item = match.group(1).upper()
            candidates.setdefault(item, []).append((i, match.group(2).strip()))

    warnings = []
    starts = []
    for item, hits in candidates.items():
        if len(hits) > 1:
            warnings.append(
                f"Item {item}: {len(hits)} heading-like lines, "
                f"using the last one (line {hits[-1][0] + 1})"
            )
        index, title = hits[-1]  # the real heading comes after any table of contents
        starts.append((index, item, title))
    starts.sort()

    # Sanity checks: are the Items in the normal order, and are any missing?
    order = [EXPECTED_ITEMS.index(item) for _, item, _ in starts if item in EXPECTED_ITEMS]
    if order != sorted(order):
        warnings.append("Items are out of order - check the headings")
    for item in EXPECTED_ITEMS:
        if item not in candidates:
            warnings.append(f"Item {item}: not found")

    # Each section runs from its heading to the next heading
    sections = []
    if starts and starts[0][0] > 0:
        sections.append(
            {
                "item": "front",
                "title": "Cover page and table of contents",
                "start_line": 1,
                "end_line": starts[0][0],
                "text": "\n".join(lines[: starts[0][0]]),
            }
        )
    for n, (index, item, title) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        sections.append(
            {
                "item": item,
                "title": title,
                "start_line": index + 1,
                "end_line": end,
                "text": "\n".join(lines[index + 1 : end]).strip(),
            }
        )
    return sections, warnings


def process_all() -> None:
    for txt_path in sorted(PROCESSED_DIR.glob("*/FY*.txt")):
        ticker = txt_path.parent.name
        fiscal_year = int(txt_path.stem[2:6])
        accession = txt_path.stem.split("_", 1)[1]

        text = txt_path.read_text(encoding="utf-8")
        sections, warnings = split_sections(text)

        out_path = txt_path.with_suffix(".sections.json")
        record = {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "accession_number": accession,
            "sections": sections,
        }
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print(f"{ticker} FY{fiscal_year}: {len(sections)} sections -> {out_path}")
        for s in sections:
            print(
                f"  {s['item']:>5}  {s['title'][:42]:<42} "
                f"lines {s['start_line']:>5}-{s['end_line']:<5} {len(s['text']):>8,} chars"
            )
        for warning in warnings:
            print(f"  WARNING: {warning}")


if __name__ == "__main__":
    process_all()