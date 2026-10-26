import time
from pathlib import Path

import requests

from src.config import PINNED_FILINGS
from src.list_filings import HEADERS, get_10k_filings

RAW_DIR = Path("data/raw")
PAUSE_SECONDS = 0.5  # be polite: the SEC allows 10 requests/second, we use ~2


def find_document_name(cik: str, accession_number: str) -> str:
    """Look up the main document's filename for a pinned filing."""
    for filing in get_10k_filings(cik, n=50):
        if filing["accession_number"] == accession_number:
            return filing["document"]
    raise ValueError(f"Accession {accession_number} not found for CIK {cik}")


def filing_url(cik: str, accession_number: str, document: str) -> str:
    """Build the download URL. EDGAR wants the CIK without leading zeros
    and the accession number without dashes."""
    cik_plain = str(int(cik))
    accession_plain = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_plain}/{accession_plain}/{document}"
    )


def download_filing(filing: dict) -> Path:
    out_dir = RAW_DIR / filing["ticker"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"FY{filing['fiscal_year']}_{filing['accession_number']}.htm"

    if out_path.exists():
        print(f"skip (already downloaded): {out_path}")
        return out_path

    document = find_document_name(filing["cik"], filing["accession_number"])
    time.sleep(PAUSE_SECONDS)

    url = filing_url(filing["cik"], filing["accession_number"], document)
    print(f"downloading {url}")
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    out_path.write_bytes(response.content)  # save exactly what the SEC sent
    print(f"saved {out_path} ({len(response.content) / 1_000_000:.1f} MB)")
    time.sleep(PAUSE_SECONDS)
    return out_path


if __name__ == "__main__":
    for filing in PINNED_FILINGS:
        download_filing(filing)