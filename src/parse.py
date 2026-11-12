import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

# Tags that start a new line of text when they open or close
BLOCK_TAGS = ["div", "p", "br", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"]

# A page footer looks like "Apple Inc. | 2025 Form 10-K | 21"
FOOTER_RE = re.compile(r"^(?P<company>.+?) \| \d{4} Form 10-K \| (?P<page>\d+)$")


def strip_page_furniture(lines: list[str]) -> tuple[list[str], list[dict]]:
    """Remove page footers and the company name repeated at the top of the next
    page. Remember where each page ended, so we can cite page numbers later."""
    kept: list[str] = []
    pages: list[dict] = []
    header_to_skip = None
    for line in lines:
        footer = FOOTER_RE.match(line)
        if footer:
            pages.append({"page": int(footer.group("page")), "end_line": len(kept)})
            header_to_skip = footer.group("company")
            continue
        if header_to_skip is not None and line == header_to_skip:
            header_to_skip = None
            continue
        header_to_skip = None
        kept.append(line)
    return kept, pages


def html_to_text(html: str) -> tuple[str, list[dict]]:
    """Turn a raw EDGAR filing into clean, readable text plus a page map."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove everything that is not visible content
    for tag in soup.find_all(["script", "style", "ix:header"]):
        if not tag.decomposed:
            tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
        if not tag.decomposed:
            tag.decompose()

    # 2. Collapse the line breaks and runs of spaces inside the source text
    for s in soup.find_all(string=True):
        if type(s) is NavigableString:
            s.replace_with(re.sub(r"\s+", " ", s))

    # 3. Mark where lines break (block tags) and where table cells end.
    #    Inside a table cell we use a space, not a line break, so a cell's text
    #    stays on one line. Only table rows start new lines.
    for cell in soup.find_all(["td", "th"]):
        cell.append(" | ")
    for tag in soup.find_all(BLOCK_TAGS):
        in_cell = tag.name not in ("tr", "table") and tag.find_parent(["td", "th"]) is not None
        separator = " " if in_cell else "\n"
        tag.insert_before(separator)
        tag.insert_after(separator)

    text = soup.get_text().replace("\xa0", " ")

    # 4. Tidy each line and drop empty ones
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line)
        line = re.sub(r"(?:\s*\|\s*){2,}", " | ", line)  # many empty cells -> one separator
        line = line.replace("$ |", "$").replace("| )", ")").replace("| %", "%")
        line = line.strip(" |")
        line = re.sub(r"^•(?=\S)", "• ", line)  # bullet glued to its text
        if line:
            lines.append(line)

    # 5. Remove page footers and repeated page headers
    lines, pages = strip_page_furniture(lines)
    return "\n".join(lines), pages


def process_all() -> None:
    for raw_path in sorted(RAW_DIR.glob("*/*.htm")):
        html = raw_path.read_text(encoding="utf-8")
        text, pages = html_to_text(html)

        out_dir = PROCESSED_DIR / raw_path.parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (raw_path.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")
        pages_path = out_path.with_suffix(".pages.json")
        pages_path.write_text(json.dumps(pages, indent=1), encoding="utf-8")

        print(raw_path.name)
        print(f"  HTML chars: {len(html):,} -> text chars: {len(text):,}")
        print(f"  lines: {text.count(chr(10)) + 1:,}")
        print(f"  page footers found: {len(pages)}")
        print(f"  leftover 'us-gaap:' mentions: {text.count('us-gaap:')}")
        print(f"  saved {out_path}")


if __name__ == "__main__":
    process_all()