def download_ghcnd_data(folder: str, output1: str, output2: str) -> None:
    import requests
    import pandas as pd
    from datetime import date, datetime
    import os
    import time

    token = faasr_secret("NOAA_CDO_TOKEN")

    STATION = "GHCND:USC00351877"
    DATASET = "GHCND"
    DATATYPES = ["PRCP", "TMAX", "TMIN"]
    BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"
    headers = {"token": token}

    today = date.today()
    current_year = today.year

    def fetch_ghcnd(start_date, end_date):
        records = []
        limit = 1000
        offset = 1
        while True:
            params = {
                "datasetid": DATASET,
                "stationid": STATION,
                "datatypeid": ",".join(DATATYPES),
                "startdate": str(start_date),
                "enddate": str(end_date),
                "units": "metric",
                "limit": limit,
                "offset": offset,
            }
            resp = requests.get(BASE_URL, headers=headers, params=params, timeout=60)
            if resp.status_code == 429:
                faasr_log("Rate limited; waiting 10s")
                time.sleep(10)
                continue
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            records.extend(results)
            meta = data.get("metadata", {}).get("resultset", {})
            total = int(meta.get("count", len(results)))
            if not results or offset + limit - 1 >= total:
                break
            offset += limit
            time.sleep(0.25)
        return records

    # --- Current year ---
    faasr_log(f"Fetching current year ({current_year}) GHCND data for USC00351877")
    curr_records = fetch_ghcnd(date(current_year, 1, 1), today)
    if not curr_records:
        msg = f"No GHCND data returned for station USC00351877 year {current_year}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    curr_dict = {}
    for r in curr_records:
        d = r["date"][:10]
        curr_dict.setdefault(d, {})[r["datatype"]] = r["value"]

    curr_rows = [
        {"date": d, "PRCP": v.get("PRCP"), "TMAX": v.get("TMAX"), "TMIN": v.get("TMIN")}
        for d, v in sorted(curr_dict.items())
    ]
    curr_df = pd.DataFrame(curr_rows, columns=["date", "PRCP", "TMAX", "TMIN"])
    faasr_log(f"Current year: {len(curr_df)} day records")

    curr_csv = "/tmp/current_year_weather.csv"
    curr_df.to_csv(curr_csv, index=False)
    faasr_put_file(local_file=curr_csv, remote_folder=folder, remote_file=output1)
    os.remove(curr_csv)

    # --- 10-year daily average (prior 10 full calendar years) ---
    end_year = current_year - 1
    start_year = end_year - 9
    faasr_log(f"Fetching 10-year historical data ({start_year}–{end_year})")

    all_hist = []
    for yr in range(start_year, end_year + 1):
        faasr_log(f"  Fetching year {yr}")
        recs = fetch_ghcnd(date(yr, 1, 1), date(yr, 12, 31))
        if not recs:
            faasr_log(f"  WARNING: no records for year {yr}")
        all_hist.extend(recs)
        time.sleep(0.25)

    if not all_hist:
        msg = f"No GHCND historical data returned for {start_year}–{end_year}"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    hist_rows = []
    for r in all_hist:
        d = r["date"][:10]
        dt_obj = datetime.strptime(d, "%Y-%m-%d")
        hist_rows.append({
            "month": dt_obj.month,
            "day": dt_obj.day,
            "datatype": r["datatype"],
            "value": float(r["value"]),
        })

    hist_df = pd.DataFrame(hist_rows)
    avg_df = (
        hist_df.groupby(["month", "day", "datatype"])["value"]
        .mean()
        .reset_index()
    )
    pivot_df = avg_df.pivot_table(
        index=["month", "day"], columns="datatype", values="value"
    ).reset_index()
    pivot_df.columns.name = None

    for dt in DATATYPES:
        if dt not in pivot_df.columns:
            pivot_df[dt] = float("nan")
    pivot_df = pivot_df.rename(columns={dt: f"{dt}_avg" for dt in DATATYPES})
    pivot_df = pivot_df.sort_values(["month", "day"]).reset_index(drop=True)
    pivot_df = pivot_df[["month", "day", "PRCP_avg", "TMAX_avg", "TMIN_avg"]]

    faasr_log(f"10-year avg: {len(pivot_df)} day-of-year rows")

    avg_csv = "/tmp/ten_year_avg_weather.csv"
    pivot_df.to_csv(avg_csv, index=False)
    faasr_put_file(local_file=avg_csv, remote_folder=folder, remote_file=output2)
    os.remove(avg_csv)

    faasr_log("download_ghcnd_data complete")
