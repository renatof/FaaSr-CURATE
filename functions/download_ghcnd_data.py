def download_ghcnd_data(folder: str, output1: str, output2: str) -> None:
    import os
    import tempfile
    from datetime import datetime
    import pandas as pd
    from meteostat import daily, Provider, stations, Point

    current_year = datetime.now().year
    today = datetime.now()

    # Find the nearest station with GHCND prcp/tmax/tmin data to Corvallis OR.
    # USC00351862 is the target COOP station; fall back to nearest available GHCND
    # station in meteostat if USC00351862 is not present.
    corvallis = Point(44.5381, -123.2836, 70)
    nearby_df = stations.nearby(corvallis)

    ghcnd_station_id = None
    for sid in nearby_df.index.tolist():
        inv = stations.inventory(sid, providers=[Provider.GHCND])
        if inv.df is not None:
            params = [str(p.value) for p in inv.parameters]
            if 'prcp' in params and 'tmax' in params and 'tmin' in params:
                ghcnd_station_id = sid
                break

    if ghcnd_station_id is None:
        msg = "No nearby GHCND station with prcp/tmax/tmin data found near Corvallis OR"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    faasr_log(f"Using meteostat station '{ghcnd_station_id}' (nearest GHCND station to Corvallis OR USC00351862)")

    # --- Current calendar year: Jan 1 to today ---
    start_current = datetime(current_year, 1, 1)
    faasr_log(f"Fetching {current_year} daily data...")

    ts_current = daily(ghcnd_station_id, start_current, today, providers=[Provider.GHCND])
    df_current = ts_current.fetch()

    if df_current is None or df_current.empty:
        msg = f"No GHCND data returned for station '{ghcnd_station_id}' in {current_year}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    for col in ('prcp', 'tmax', 'tmin'):
        if col not in df_current.columns:
            faasr_log(f"ERROR: Column '{col}' missing from GHCND response")
            raise RuntimeError(f"Column '{col}' not present in GHCND daily data")

    df_cur = df_current[['prcp', 'tmax', 'tmin']].copy()
    df_cur.index.name = 'date'
    df_cur.reset_index(inplace=True)
    df_cur['date'] = pd.to_datetime(df_cur['date']).dt.strftime('%Y-%m-%d')
    # Convert: mm -> inches, °C -> °F
    df_cur['PRCP'] = df_cur['prcp'].astype(float) * 0.0393701
    df_cur['TMAX'] = df_cur['tmax'].astype(float) * 9.0 / 5.0 + 32.0
    df_cur['TMIN'] = df_cur['tmin'].astype(float) * 9.0 / 5.0 + 32.0
    df_cur = df_cur[['date', 'PRCP', 'TMAX', 'TMIN']]

    # --- Previous 10 full calendar years ---
    hist_end_year = current_year - 1
    hist_start_year = current_year - 10
    hist_start = datetime(hist_start_year, 1, 1)
    hist_end = datetime(hist_end_year, 12, 31)

    faasr_log(f"Fetching historical data {hist_start_year}–{hist_end_year} for 10-year average...")

    ts_hist = daily(ghcnd_station_id, hist_start, hist_end, providers=[Provider.GHCND])
    df_hist_raw = ts_hist.fetch()

    if df_hist_raw is None or df_hist_raw.empty:
        msg = f"No historical GHCND data for station '{ghcnd_station_id}' ({hist_start_year}-{hist_end_year})"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    df_hist = df_hist_raw[['prcp', 'tmax', 'tmin']].copy()
    df_hist.index.name = 'date'
    df_hist.reset_index(inplace=True)
    df_hist['date'] = pd.to_datetime(df_hist['date'])
    df_hist['PRCP'] = df_hist['prcp'].astype(float) * 0.0393701
    df_hist['TMAX'] = df_hist['tmax'].astype(float) * 9.0 / 5.0 + 32.0
    df_hist['TMIN'] = df_hist['tmin'].astype(float) * 9.0 / 5.0 + 32.0

    # Average by month+day (MM-DD) across all 10 years
    df_hist['month_day'] = df_hist['date'].dt.strftime('%m-%d')
    df_avg = (
        df_hist.groupby('month_day')[['PRCP', 'TMAX', 'TMIN']]
        .mean()
        .reset_index()
        .rename(columns={'month_day': 'date'})
        .sort_values('date')
        .reset_index(drop=True)
    )

    # Save to temp files and upload
    fd1, current_tmp = tempfile.mkstemp(suffix='.csv')
    os.close(fd1)
    fd2, avg_tmp = tempfile.mkstemp(suffix='.csv')
    os.close(fd2)

    try:
        df_cur.to_csv(current_tmp, index=False)
        df_avg.to_csv(avg_tmp, index=False)

        faasr_log(f"Uploading {output1} ({len(df_cur)} rows of current-year daily data)...")
        faasr_put_file(local_file=current_tmp, remote_folder=folder, remote_file=output1)

        faasr_log(f"Uploading {output2} ({len(df_avg)} rows of 10-year average data)...")
        faasr_put_file(local_file=avg_tmp, remote_folder=folder, remote_file=output2)

        faasr_log("download_ghcnd_data complete")
    finally:
        os.unlink(current_tmp)
        os.unlink(avg_tmp)
