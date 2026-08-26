def download_ghcnd_data(folder: str, output1: str, output2: str) -> None:
    import os
    import datetime
    import tempfile
    import pandas as pd
    from meteostat import daily, Station, Parameter

    today = datetime.date.today()
    current_year = today.year

    # GHCND station USW00024232 maps to meteostat internal ID 72694 (Salem McNary Field).
    # This is the nearest GHCND-covered station to Corvallis OR; USW00024232 is the
    # GHCND identifier listed in the spec.
    STATION_ID = "72694"  # meteostat ID for GHCND:USW00024232

    # ---- Current year data ----
    faasr_log(f"Fetching {current_year} daily data for Corvallis OR (GHCND USW00024232 / meteostat {STATION_ID})")
    start_current = datetime.date(current_year, 1, 1)
    end_current = today
    ts_current = daily(
        Station(STATION_ID),
        start_current,
        end_current,
        parameters=[Parameter.TMAX, Parameter.TMIN, Parameter.PRCP],
    )
    if ts_current.empty:
        msg = f"No current-year data returned from meteostat station {STATION_ID} for {current_year}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)
    current_raw = ts_current.fetch()
    if current_raw is None or current_raw.empty:
        msg = f"Empty fetch result from meteostat station {STATION_ID} for {current_year}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    current_df = current_raw.reset_index().rename(
        columns={"time": "date", "tmax": "TMAX", "tmin": "TMIN", "prcp": "PRCP"}
    )
    current_df["date"] = pd.to_datetime(current_df["date"]).dt.strftime("%Y-%m-%d")
    current_out = current_df[["date", "PRCP", "TMAX", "TMIN"]].copy()
    faasr_log(f"Current year: {len(current_out)} daily rows")

    # ---- 10-year historical average ----
    hist_end_year = current_year - 1
    hist_start_year = current_year - 10
    faasr_log(f"Fetching 10-year historical data ({hist_start_year}–{hist_end_year}) from meteostat station {STATION_ID}")
    hist_start = datetime.date(hist_start_year, 1, 1)
    hist_end = datetime.date(hist_end_year, 12, 31)
    ts_hist = daily(
        Station(STATION_ID),
        hist_start,
        hist_end,
        parameters=[Parameter.TMAX, Parameter.TMIN, Parameter.PRCP],
    )
    if ts_hist.empty:
        msg = f"No historical data from meteostat station {STATION_ID} for {hist_start_year}–{hist_end_year}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)
    hist_raw = ts_hist.fetch()
    if hist_raw is None or hist_raw.empty:
        msg = f"Empty 10-year fetch result from meteostat station {STATION_ID}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    hist_df = hist_raw.reset_index().rename(
        columns={"time": "date", "tmax": "TMAX", "tmin": "TMIN", "prcp": "PRCP"}
    )
    hist_df["day_of_year"] = pd.to_datetime(hist_df["date"]).dt.dayofyear
    avg_out = (
        hist_df.groupby("day_of_year")[["PRCP", "TMAX", "TMIN"]]
        .mean()
        .reset_index()
    )
    faasr_log(f"10-year average: {len(avg_out)} day-of-year entries")

    # ---- Write and upload ----
    with tempfile.TemporaryDirectory() as tmpdir:
        local_current = os.path.join(tmpdir, "current.csv")
        local_avg = os.path.join(tmpdir, "avg.csv")

        current_out.to_csv(local_current, index=False)
        avg_out.to_csv(local_avg, index=False)

        faasr_log(f"Uploading {output1}")
        faasr_put_file(local_file=local_current, remote_folder=folder, remote_file=output1)

        faasr_log(f"Uploading {output2}")
        faasr_put_file(local_file=local_avg, remote_folder=folder, remote_file=output2)

    faasr_log("download_ghcnd_data complete")
