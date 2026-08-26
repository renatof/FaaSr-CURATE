def fit_tmax_regression(folder: str, input1: str, output1: str, output2: str) -> None:
    import os
    import tempfile
    import pandas as pd
    from scipy.stats import linregress

    local_input = os.path.join(tempfile.gettempdir(), input1)
    faasr_get_file(local_file=local_input, remote_folder=folder, remote_file=input1)

    df = pd.read_csv(local_input, parse_dates=["date"])
    df = df.dropna(subset=["TMAX"])
    if df.empty:
        msg = "No valid TMAX rows in input after dropping NaN"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    df["day_of_year"] = df["date"].dt.dayofyear

    slope, intercept, r_value, p_value, std_err = linregress(df["day_of_year"], df["TMAX"])

    faasr_log(
        f"TMAX regression: slope={slope:.4f}, intercept={intercept:.4f}, "
        f"r2={r_value**2:.4f}, p_value={p_value:.4e}"
    )

    doy_min = int(df["day_of_year"].min())
    doy_max = int(df["day_of_year"].max())
    day_range = range(doy_min, doy_max + 1)
    fitted_df = pd.DataFrame({
        "day_of_year": list(day_range),
        "TMAX_fitted": [slope * d + intercept for d in day_range],
    })
    fitted_df["day_of_year"] = fitted_df["day_of_year"].astype(int)

    summary_df = pd.DataFrame([{
        "slope": slope,
        "intercept": intercept,
        "r_value": r_value,
        "p_value": p_value,
        "std_err": std_err,
    }])

    with tempfile.TemporaryDirectory() as tmpdir:
        local_fitted = os.path.join(tmpdir, output1)
        local_summary = os.path.join(tmpdir, output2)

        fitted_df.to_csv(local_fitted, index=False)
        summary_df.to_csv(local_summary, index=False)

        faasr_log(f"Uploading {output1} ({len(fitted_df)} rows)")
        faasr_put_file(local_file=local_fitted, remote_folder=folder, remote_file=output1)

        faasr_log(f"Uploading {output2}")
        faasr_put_file(local_file=local_summary, remote_folder=folder, remote_file=output2)

    faasr_log("fit_tmax_regression complete")
