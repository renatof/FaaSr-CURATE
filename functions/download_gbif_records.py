import os
import pandas as pd
from pygbif import occurrences as occ

def download_gbif_records(folder: str, output1: str) -> None:
    local_file = "castor_canadensis_raw.csv"
    species_name = "Castor canadensis"
    page_limit = 300
    # GBIF search API caps retrievable records at offset + limit <= 100,000
    max_offset = 100_000

    faasr_log(f"Starting GBIF download for '{species_name}'")

    all_records = []
    offset = 0

    while offset < max_offset:
        effective_limit = min(page_limit, max_offset - offset)
        faasr_log(f"Fetching GBIF records: offset={offset}, limit={effective_limit}")

        result = occ.search(
            scientificName=species_name,
            limit=effective_limit,
            offset=offset,
        )

        records = result.get("results")
        if not records:
            faasr_log("No records returned in this page; stopping pagination")
            break

        all_records.extend(records)
        total_available = result.get("count", "unknown")
        faasr_log(
            f"Cumulative records fetched: {len(all_records)} "
            f"(GBIF total available: {total_available})"
        )

        if result.get("endOfRecords", True):
            faasr_log("Reached end of GBIF records")
            break

        offset += effective_limit

    if not all_records:
        msg = f"GBIF returned zero records for '{species_name}'"
        faasr_log(msg)
        raise RuntimeError(msg)

    faasr_log(f"Building DataFrame from {len(all_records)} records")
    df = pd.DataFrame(all_records)
    df.to_csv(local_file, index=False)
    faasr_log(f"Wrote {len(df)} rows, {len(df.columns)} columns to {local_file}")

    faasr_put_file(local_file=local_file, remote_folder=folder, remote_file=output1)
    faasr_log(f"Uploaded '{output1}' to folder '{folder}'")

    os.remove(local_file)
