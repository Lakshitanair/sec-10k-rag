import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

# Tags that start a new line of text when they open or close
BLOCK_TAGS = ["div", "p", "br", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"]


def html_to_text(html: str) -> str:
    """Turn a raw EDGAR filing into clean, readable text."""
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

    # 3. Mark where lines break (block tags) and where table cells end
    for cell in soup.find_all(["td", "th"]):
        cell.append(" | ")
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text().replace("\xa0", " ")

    # 4. Tidy each line and drop empty ones
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line)
        line = re.sub(r"(?:\s*\|\s*){2,}", " | ", line)  # many empty cells -> one separator
        line = line.replace("$ |", "$").replace("| )", ")").replace("| %", "%")
        line = line.strip(" |")
        if line:
            lines.append(line)
    return "\n".join(lines)


def process_all() -> None:
    for raw_path in sorted(RAW_DIR.glob("*/*.htm")):
        html = raw_path.read_text(encoding="utf-8")
        text = html_to_text(html)

        out_dir = PROCESSED_DIR / raw_path.parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (raw_path.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")

        print(raw_path.name)
        print(f"  HTML chars: {len(html):,} -> text chars: {len(text):,}")
        print(f"  lines: {text.count(chr(10)) + 1:,}")
        print(f"  leftover 'us-gaap:' mentions: {text.count('us-gaap:')}")
        print(f"  saved {out_path}")


if __name__ == "__main__":
    process_all()