import os
import time
import tempfile
from datetime import date

import pandas as pd
import requests


def download_weather_data(folder: str, output1: str, output2: str) -> None:
    token = faasr_secret("NOAA_API_TOKEN")

    today = date.today()
    current_year = today.year

    station_id = "GHCND:USW00024232"  # Corvallis Municipal Airport
    base_url = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"
    headers = {"token": token}

    def fetch_year(year):
        start = date(year, 1, 1)
        end = date(year, 12, 31) if year < current_year else today
        all_results = []
        offset = 1
        while True:
            params = {
                "datasetid": "GHCND",
                "stationid": station_id,
                "datatypeid": "PRCP,TMAX,TMIN",
                "startdate": str(start),
                "enddate": str(end),
                "limit": 1000,
                "offset": offset,
                "units": "metric",
            }
            resp = requests.get(base_url, headers=headers, params=params, timeout=60)
            if resp.status_code == 429:
                time.sleep(2)
                resp = requests.get(base_url, headers=headers, params=params, timeout=60)
            resp.raise_for_status()
            body = resp.json()
            results = body.get("results", [])
            if not results:
                break
            all_results.extend(results)
            total = body.get("metadata", {}).get("resultset", {}).get("count", 0)
            if offset + len(results) - 1 >= total:
                break
            offset += 1000
            time.sleep(0.25)
        return all_results

    def results_to_wide(results):
        rows = {}
        for r in results:
            dt = r["date"][:10]
            rows.setdefault(dt, {"date": dt})[r["datatype"]] = r["value"]
        df = pd.DataFrame(list(rows.values()))
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        for col in ("PRCP", "TMAX", "TMIN"):
            if col not in df.columns:
                df[col] = float("nan")
        return df[["date", "PRCP", "TMAX", "TMIN"]]

    # --- Current year ---
    faasr_log(f"Fetching current-year ({current_year}) data from NOAA CDO API...")
    cur_results = fetch_year(current_year)
    if not cur_results:
        raise RuntimeError(
            f"NOAA CDO API returned no data for station {station_id}, year {current_year}"
        )
    df_current = results_to_wide(cur_results)
    faasr_log(f"Current-year rows: {len(df_current)}")

    # --- Historical 10 years ---
    faasr_log(f"Fetching historical data for years {current_year - 10} to {current_year - 1}...")
    hist_frames = []
    for yr in range(current_year - 10, current_year):
        faasr_log(f"  Fetching {yr}...")
        yr_results = fetch_year(yr)
        if yr_results:
            hist_frames.append(results_to_wide(yr_results))
        time.sleep(0.25)

    if not hist_frames:
        raise RuntimeError("NOAA CDO API returned no historical data")

    df_hist = pd.concat(hist_frames, ignore_index=True)

    # Compute 10-year daily average keyed by calendar day (MM-DD)
    df_hist["calendar_day"] = df_hist["date"].dt.strftime("%m-%d")
    df_avg = (
        df_hist.groupby("calendar_day")[["PRCP", "TMAX", "TMIN"]]
        .mean()
        .reset_index()
        .rename(columns={"calendar_day": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    faasr_log(f"10-year average rows: {len(df_avg)}")

    # --- Upload ---
    with tempfile.TemporaryDirectory() as tmpdir:
        cur_path = os.path.join(tmpdir, "current.csv")
        avg_path = os.path.join(tmpdir, "avg.csv")
        df_current.to_csv(cur_path, index=False)
        df_avg.to_csv(avg_path, index=False)

        faasr_put_file(local_file=cur_path, remote_folder=folder, remote_file=output1)
        faasr_put_file(local_file=avg_path, remote_folder=folder, remote_file=output2)

    faasr_log("download_weather_data complete")
