import os
import tempfile

import numpy as np
import pandas as pd


def fit_prcp_regression(folder: str, input1: str, output1: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        local_input = os.path.join(tmpdir, "current_weather.csv")
        faasr_get_file(local_file=local_input, remote_folder=folder, remote_file=input1)

        df = pd.read_csv(local_input, parse_dates=["date"])

        df = df.dropna(subset=["PRCP"])
        if df.empty:
            raise RuntimeError("No valid PRCP observations found in the input CSV")

        df["day_of_year"] = df["date"].dt.dayofyear
        x = df["day_of_year"].values.astype(float)
        y = df["PRCP"].values.astype(float)

        faasr_log(f"Fitting linear regression on {len(x)} PRCP observations")

        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        intercept = coeffs[1]

        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot != 0.0 else 0.0

        faasr_log(f"Regression: slope={slope:.6f}, intercept={intercept:.6f}, r_squared={r_squared:.6f}")

        params_df = pd.DataFrame([{"slope": slope, "intercept": intercept, "r_squared": r_squared}])

        local_output = os.path.join(tmpdir, "params.csv")
        params_df.to_csv(local_output, index=False)

        faasr_put_file(local_file=local_output, remote_folder=folder, remote_file=output1)

    faasr_log("fit_prcp_regression complete")
