import datetime
import os
import pandas as pd
from meteostat import stations, Station, daily
from meteostat.enumerations import Parameter


# Corvallis Municipal Airport / Dry Creek station (USAF 726945 / WBAN 24202)
STATION_ID = "KCVO0"


def download_ghcnd_data(folder: str, output1: str, output2: str) -> None:
    faasr_log(f"Fetching GHCND data for Corvallis OR, station {STATION_ID}")

    st = stations.meta(STATION_ID)
    if st is None:
        msg = f"Station {STATION_ID} not found in meteostat database"
        faasr_log(msg)
        raise RuntimeError(msg)

    params = [Parameter.PRCP, Parameter.TMAX, Parameter.TMIN]
    today = datetime.date.today()
    current_year = today.year

    # --- Current year observations ---
    cy_start = datetime.datetime(current_year, 1, 1)
    cy_end = datetime.datetime(current_year, today.month, today.day)

    faasr_log(f"Fetching current-year data {cy_start.date()} to {cy_end.date()}")
    cy_ts = daily(st, cy_start, cy_end, parameters=params)
    cy_df = cy_ts.fetch()
    if cy_df is None or cy_df.empty:
        msg = "No current-year data returned from meteostat for station " + STATION_ID
        faasr_log(msg)
        raise RuntimeError(msg)

    cy_df.index.name = "date"
    cy_df = cy_df.rename(columns={"prcp": "PRCP", "tmax": "TMAX", "tmin": "TMIN"})
    cy_df = cy_df[["PRCP", "TMAX", "TMIN"]].reset_index()
    cy_df["date"] = pd.to_datetime(cy_df["date"]).dt.date
    faasr_log(f"Current-year rows: {len(cy_df)}")

    # --- 10-year historical daily averages (past 10 complete years) ---
    hist_end = datetime.datetime(current_year - 1, 12, 31)
    hist_start = datetime.datetime(current_year - 10, 1, 1)

    faasr_log(f"Fetching historical data {hist_start.date()} to {hist_end.date()}")
    hist_ts = daily(st, hist_start, hist_end, parameters=params)
    hist_df = hist_ts.fetch()
    if hist_df is None or hist_df.empty:
        msg = "No historical data returned from meteostat for station " + STATION_ID
        faasr_log(msg)
        raise RuntimeError(msg)

    hist_df.index.name = "date"
    hist_df = hist_df.rename(columns={"prcp": "PRCP", "tmax": "TMAX", "tmin": "TMIN"})
    hist_df["day_of_year"] = pd.to_datetime(hist_df.index).dayofyear
    avg_df = (
        hist_df.groupby("day_of_year")
        .agg(PRCP_avg=("PRCP", "mean"), TMAX_avg=("TMAX", "mean"), TMIN_avg=("TMIN", "mean"))
        .reset_index()
    )
    faasr_log(f"10-year average rows: {len(avg_df)}")

    # --- Save and upload current-year CSV ---
    cy_local = "current_year_observations.csv"
    cy_df.to_csv(cy_local, index=False)
    faasr_log(f"Uploading {output1}")
    faasr_put_file(local_file=cy_local, remote_folder=folder, remote_file=output1)
    os.remove(cy_local)

    # --- Save and upload 10-year averages CSV ---
    avg_local = "ten_year_daily_averages.csv"
    avg_df.to_csv(avg_local, index=False)
    faasr_log(f"Uploading {output2}")
    faasr_put_file(local_file=avg_local, remote_folder=folder, remote_file=output2)
    os.remove(avg_local)

    faasr_log("download_ghcnd_data complete")
