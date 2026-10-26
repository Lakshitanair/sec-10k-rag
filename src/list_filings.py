import os

import requests
from dotenv import load_dotenv

# Read the .env file and make its settings available to the program
load_dotenv()

USER_AGENT = os.getenv("SEC_USER_AGENT")
if not USER_AGENT:
    raise RuntimeError("SEC_USER_AGENT is missing. Add it to your .env file.")

# The SEC requires every automated request to identify who is asking
HEADERS = {"User-Agent": USER_AGENT}


def get_10k_filings(cik: str, n: int = 3) -> list[dict]:
    """Return the n most recent 10-K filings for a company."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()  # stop with a clear error if the request failed

    recent = response.json()["filings"]["recent"]

    filings = []
    for i, form in enumerate(recent["form"]):
        if form == "10-K":  # skip 10-Qs, 8-Ks, and every other form type
            filings.append(
                {
                    "accession_number": recent["accessionNumber"][i],
                    "filing_date": recent["filingDate"][i],
                    "fiscal_year_end": recent["reportDate"][i],
                    "document": recent["primaryDocument"][i],
                }
            )

    # Don't trust the feed's order: sort newest first ourselves
    filings.sort(key=lambda f: f["filing_date"], reverse=True)
    return filings[:n]


if __name__ == "__main__":
    for f in get_10k_filings("0000320193"):  # Apple
        print(
            f"filed {f['filing_date']} | "
            f"fiscal year-end {f['fiscal_year_end']} | "
            f"{f['accession_number']} | {f['document']}"
        )