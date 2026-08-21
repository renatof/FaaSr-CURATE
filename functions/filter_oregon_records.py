import os
import math
import pandas as pd

# Approximate bounding box for Oregon
LAT_MIN, LAT_MAX = 42.0, 46.5
LON_MIN, LON_MAX = -124.6, -116.5

def filter_oregon_records(folder: str, input1: str, output1: str) -> None:
    local_input = "castor_canadensis_raw.csv"
    local_output = "castor_canadensis_oregon.csv"

    faasr_get_file(local_file=local_input, remote_folder=folder, remote_file=input1)
    faasr_log(f"Downloaded '{input1}' from folder '{folder}'")

    df = pd.read_csv(local_input)
    faasr_log(f"Loaded {len(df)} records")

    lat = pd.to_numeric(df["decimalLatitude"], errors="coerce")
    lon = pd.to_numeric(df["decimalLongitude"], errors="coerce")

    mask = (
        lat.notna() & lon.notna() &
        (lat >= LAT_MIN) & (lat <= LAT_MAX) &
        (lon >= LON_MIN) & (lon <= LON_MAX)
    )

    oregon_df = df[mask].copy()
    faasr_log(f"Filtered to {len(oregon_df)} Oregon records (lat {LAT_MIN}–{LAT_MAX}, lon {LON_MIN}–{LON_MAX})")

    oregon_df.to_csv(local_output, index=False)

    faasr_put_file(local_file=local_output, remote_folder=folder, remote_file=output1)
    faasr_log(f"Uploaded '{output1}' to folder '{folder}'")

    os.remove(local_input)
    os.remove(local_output)
