import os
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d


def _fill_column_spline(series: pd.Series, x: np.ndarray) -> pd.Series:
    """Fill NaN values in series using cubic spline interpolation over x."""
    valid = series.notna()
    if valid.sum() < 4:
        # Not enough points for cubic spline; fall back to linear or skip
        if valid.sum() < 2:
            return series
        f = interp1d(x[valid], series[valid], kind='linear', bounds_error=False, fill_value='extrapolate')
    else:
        f = interp1d(x[valid], series[valid], kind='cubic', bounds_error=False, fill_value='extrapolate')
    filled = series.copy()
    mask = series.isna()
    filled[mask] = f(x[mask])
    return filled


def fill_climate_gaps(folder: str, input1: str, input2: str, output1: str, output2: str) -> None:
    faasr_log("fill_climate_gaps: downloading input files")

    cy_local = "cy_obs_raw.csv"
    avg_local = "ten_yr_avg_raw.csv"

    faasr_get_file(local_file=cy_local, remote_folder=folder, remote_file=input1)
    faasr_get_file(local_file=avg_local, remote_folder=folder, remote_file=input2)

    cy_df = pd.read_csv(cy_local)
    avg_df = pd.read_csv(avg_local)
    os.remove(cy_local)
    os.remove(avg_local)

    faasr_log(f"Current-year rows: {len(cy_df)}, 10-yr avg rows: {len(avg_df)}")

    # --- Fill current-year observations ---
    cy_df["date"] = pd.to_datetime(cy_df["date"])
    cy_df = cy_df.sort_values("date").reset_index(drop=True)
    x_cy = cy_df["date"].dt.dayofyear.values.astype(float)

    for col in ("PRCP", "TMAX", "TMIN"):
        if col in cy_df.columns:
            nan_count = cy_df[col].isna().sum()
            if nan_count > 0:
                faasr_log(f"Filling {nan_count} NaN(s) in current-year {col}")
                cy_df[col] = _fill_column_spline(cy_df[col], x_cy)

    # --- Fill 10-year daily averages ---
    avg_df = avg_df.sort_values("day_of_year").reset_index(drop=True)
    x_avg = avg_df["day_of_year"].values.astype(float)

    for col in ("PRCP_avg", "TMAX_avg", "TMIN_avg"):
        if col in avg_df.columns:
            nan_count = avg_df[col].isna().sum()
            if nan_count > 0:
                faasr_log(f"Filling {nan_count} NaN(s) in 10-yr avg {col}")
                avg_df[col] = _fill_column_spline(avg_df[col], x_avg)

    # --- Save filled CSVs ---
    cy_out_local = "filled_cy_obs.csv"
    avg_out_local = "filled_ten_yr_avg.csv"

    cy_df["date"] = cy_df["date"].dt.date
    cy_df.to_csv(cy_out_local, index=False)
    avg_df.to_csv(avg_out_local, index=False)

    # Upload — output filenames contain no {rank} template; upload once each
    faasr_log(f"Uploading {output1}")
    faasr_put_file(local_file=cy_out_local, remote_folder=folder, remote_file=output1)

    faasr_log(f"Uploading {output2}")
    faasr_put_file(local_file=avg_out_local, remote_folder=folder, remote_file=output2)

    os.remove(cy_out_local)
    os.remove(avg_out_local)

    faasr_log("fill_climate_gaps complete")
