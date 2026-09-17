import os
import tempfile
from datetime import date, datetime, timedelta
import requests
import pandas as pd


STATION_ID = "USC00351862"  # NWS Corvallis, OR


def _noaa_fetch(token: str, dataset: str, station: str, start_date: str, end_date: str,
                datatypes: list, limit: int = 1000) -> list:
    """Fetch records from NOAA CDO API, handling pagination."""
    base_url = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"
    headers = {"token": token}
    params = {
        "datasetid": dataset,
        "stationid": station,
        "startdate": start_date,
        "enddate": end_date,
        "datatypeid": ",".join(datatypes),
        "limit": limit,
        "offset": 1,
        "units": "standard",
    }
    results = []
    while True:
        resp = requests.get(base_url, headers=headers, params=params, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(
                f"NOAA CDO API error {resp.status_code}: {resp.text}"
            )
        body = resp.json()
        batch = body.get("results", [])
        results.extend(batch)
        meta = body.get("metadata", {}).get("resultset", {})
        count = meta.get("count", 0)
        offset = meta.get("offset", 1)
        fetched = offset + len(batch) - 1
        if fetched >= count or not batch:
            break
        params["offset"] = fetched + 1
    return results


def _records_to_daily_df(records: list) -> pd.DataFrame:
    """Pivot NOAA records list to a DataFrame with one row per date."""
    if not records:
        return pd.DataFrame(columns=["date", "PRCP", "TMAX", "TMIN"])
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    pivot = df.pivot_table(index="date", columns="datatype", values="value", aggfunc="first")
    pivot = pivot.reset_index()
    pivot.columns.name = None
    for col in ("PRCP", "TMAX", "TMIN"):
        if col not in pivot.columns:
            pivot[col] = float("nan")
    pivot = pivot[["date", "PRCP", "TMAX", "TMIN"]]
    return pivot


def download_weather_data(folder: str, output1: str, output2: str) -> None:
    token = faasr_secret("NOAA_API_TOKEN")

    today = date.today()
    current_year = today.year

    # ── 1. Current-year data ─────────────────────────────────────────────────
    cy_start = f"{current_year}-01-01"
    cy_end = today.strftime("%Y-%m-%d")
    faasr_log(f"Fetching current-year ({current_year}) data for station {STATION_ID}")
    cy_records = _noaa_fetch(
        token, "GHCND", f"GHCND:{STATION_ID}",
        cy_start, cy_end,
        ["PRCP", "TMAX", "TMIN"],
    )
    if not cy_records:
        trimmed_end = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        faasr_log(
            f"No records for {cy_start} to {cy_end}; retrying with end_date={trimmed_end} "
            f"to avoid CDO recency lag"
        )
        cy_records = _noaa_fetch(
            token, "GHCND", f"GHCND:{STATION_ID}",
            cy_start, trimmed_end,
            ["PRCP", "TMAX", "TMIN"],
        )
        if not cy_records:
            raise RuntimeError(
                f"No current-year GHCND records returned for station {STATION_ID} "
                f"from {cy_start} to {trimmed_end}. "
                f"The CDO endpoint has not yet populated current-year data for station "
                f"{STATION_ID}. GHCND records are typically delayed by days to weeks. "
                f"Suggested alternative: use the NOAA GHCN Daily flat-file endpoint at "
                f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/"
            )
        faasr_log(
            f"Warning: end date trimmed to {trimmed_end} to avoid CDO recency lag for "
            f"station {STATION_ID}"
        )
    cy_df = _records_to_daily_df(cy_records)
    faasr_log(f"Current-year rows: {len(cy_df)}")

    # ── 2. 10-year historical average ────────────────────────────────────────
    end_year = current_year - 1
    start_year = end_year - 9  # 10 complete calendar years
    hist_dfs = []
    for yr in range(start_year, end_year + 1):
        faasr_log(f"Fetching historical data for year {yr}")
        yr_records = _noaa_fetch(
            token, "GHCND", f"GHCND:{STATION_ID}",
            f"{yr}-01-01", f"{yr}-12-31",
            ["PRCP", "TMAX", "TMIN"],
        )
        if not yr_records:
            faasr_log(f"Warning: no records for year {yr}, skipping")
            continue
        yr_df = _records_to_daily_df(yr_records)
        yr_df["doy"] = pd.to_datetime(yr_df["date"]).dt.dayofyear
        hist_dfs.append(yr_df)

    if not hist_dfs:
        raise RuntimeError(
            f"No historical GHCND records returned for station {STATION_ID} "
            f"for years {start_year}–{end_year}"
        )

    hist_all = pd.concat(hist_dfs, ignore_index=True)
    avg_df = (
        hist_all.groupby("doy")[["PRCP", "TMAX", "TMIN"]]
        .mean()
        .rename(columns={"PRCP": "PRCP_avg", "TMAX": "TMAX_avg", "TMIN": "TMIN_avg"})
        .reset_index()
        .rename(columns={"doy": "day_of_year"})
    )
    faasr_log(f"10-year average rows: {len(avg_df)}")

    # ── 3. Save and upload ────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        cy_path = os.path.join(tmpdir, "cy.csv")
        avg_path = os.path.join(tmpdir, "avg.csv")

        cy_df.to_csv(cy_path, index=False)
        avg_df.to_csv(avg_path, index=False)

        faasr_put_file(local_file=cy_path, remote_folder=folder, remote_file=output1)
        faasr_log(f"Uploaded current-year data as {output1}")

        faasr_put_file(local_file=avg_path, remote_folder=folder, remote_file=output2)
        faasr_log(f"Uploaded 10-year average data as {output2}")
