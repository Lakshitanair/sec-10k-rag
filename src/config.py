"""The exact filings this project uses.

Filings are pinned by accession number so the document set never changes
underneath us, even when a company files a newer 10-K.
"""

PINNED_FILINGS = [
    {
        "ticker": "AAPL",
        "cik": "0000320193",
        "fiscal_year": 2025,
        "accession_number": "0000320193-25-000079",
    },
    {
        "ticker": "AAPL",
        "cik": "0000320193",
        "fiscal_year": 2024,
        "accession_number": "0000320193-24-000123",
    },
    {
        "ticker": "AAPL",
        "cik": "0000320193",
        "fiscal_year": 2023,
        "accession_number": "0000320193-23-000106",
    },
]