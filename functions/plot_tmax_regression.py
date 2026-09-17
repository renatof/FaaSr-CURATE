import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_tmax_regression(folder: str, input1: str, input2: str, output1: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        local_weather = os.path.join(tmpdir, "current_weather.csv")
        local_params = os.path.join(tmpdir, "params.csv")

        faasr_get_file(local_file=local_weather, remote_folder=folder, remote_file=input1)
        faasr_get_file(local_file=local_params, remote_folder=folder, remote_file=input2)

        df = pd.read_csv(local_weather, parse_dates=["date"])
        df = df.dropna(subset=["TMAX"])
        if df.empty:
            raise RuntimeError("No valid TMAX observations found in current-year weather CSV")

        df["day_of_year"] = df["date"].dt.dayofyear
        x = df["day_of_year"].values.astype(float)
        y = df["TMAX"].values.astype(float)

        params = pd.read_csv(local_params)
        slope = float(params["slope"].iloc[0])
        intercept = float(params["intercept"].iloc[0])
        r_squared = float(params["r_squared"].iloc[0])

        faasr_log(f"Plotting {len(x)} TMAX observations with regression line")

        x_line = np.array([x.min(), x.max()])
        y_line = slope * x_line + intercept

        sign = "+" if intercept >= 0 else "-"
        eq_label = f"y = {slope:.4f}·x {sign} {abs(intercept):.4f}\n$R^2$ = {r_squared:.4f}"

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(x, y, s=18, alpha=0.6, color="steelblue", label="Observed TMAX")
        ax.plot(x_line, y_line, color="tomato", linewidth=2, label=f"Regression fit\n{eq_label}")

        ax.set_title("Corvallis OR — Current Year TMAX with Linear Regression Fit")
        ax.set_xlabel("Day of Year")
        ax.set_ylabel("Max Temperature (°C)")
        ax.legend(fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.4)

        fig.tight_layout()

        local_png = os.path.join(tmpdir, "plot.png")
        fig.savefig(local_png, dpi=150)
        plt.close(fig)

        faasr_put_file(local_file=local_png, remote_folder=folder, remote_file=output1)

    faasr_log("plot_tmax_regression complete")
