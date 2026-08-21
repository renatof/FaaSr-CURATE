import os
import math
import pandas as pd

def summarize_coordinates(folder: str, input1: str, output1: str) -> None:
    local_input = "castor_canadensis_raw.csv"
    local_output = "coordinate_summary.csv"

    faasr_get_file(local_file=local_input, remote_folder=folder, remote_file=input1)
    faasr_log(f"Downloaded '{input1}' from folder '{folder}'")

    df = pd.read_csv(local_input)
    faasr_log(f"Loaded {len(df)} records")

    counts = {"valid": 0, "invalid": 0, "null": 0, "non-existent": 0}

    for _, row in df.iterrows():
        raw_lat = row.get("decimalLatitude")
        raw_lon = row.get("decimalLongitude")

        # Try to coerce to float; NaN (missing) and non-numeric strings → non-existent
        try:
            lat = float(raw_lat)
            lon = float(raw_lon)
            numeric = not (math.isnan(lat) or math.isnan(lon))
        except (TypeError, ValueError):
            numeric = False

        if not numeric:
            counts["non-existent"] += 1
            continue

        # Both are finite numbers — check for (0, 0) exactly
        if lat == 0.0 and lon == 0.0:
            counts["null"] += 1
        elif -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            counts["valid"] += 1
        else:
            counts["invalid"] += 1

    faasr_log(
        f"Coordinate summary: valid={counts['valid']}, invalid={counts['invalid']}, "
        f"null={counts['null']}, non-existent={counts['non-existent']}"
    )

    summary_df = pd.DataFrame([
        {"category": "valid",        "count": counts["valid"]},
        {"category": "invalid",      "count": counts["invalid"]},
        {"category": "null",         "count": counts["null"]},
        {"category": "non-existent", "count": counts["non-existent"]},
    ])
    summary_df.to_csv(local_output, index=False)

    faasr_put_file(local_file=local_output, remote_folder=folder, remote_file=output1)
    faasr_log(f"Uploaded '{output1}' to folder '{folder}'")

    os.remove(local_input)
    os.remove(local_output)
