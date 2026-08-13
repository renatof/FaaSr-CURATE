import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import datetime


# rank → (obs_col, avg_col, label, y_axis_label)
VARIABLE_MAP = {
    1: ("PRCP",  "PRCP_avg",  "Precipitation",    "Precipitation (mm)"),
    2: ("TMAX",  "TMAX_avg",  "Max Temperature",  "Temperature (°C)"),
    3: ("TMIN",  "TMIN_avg",  "Min Temperature",  "Temperature (°C)"),
}


def plot_climate_variable(folder: str, input1: str, input2: str, output1: str) -> None:
    r = faasr_rank()
    rank = r["rank"]

    if rank not in VARIABLE_MAP:
        msg = f"Unexpected rank {rank}; expected 1, 2, or 3"
        faasr_log(msg)
        raise RuntimeError(msg)

    obs_col, avg_col, var_label, y_label = VARIABLE_MAP[rank]
    faasr_log(f"Rank {rank}: plotting {var_label}")

    # Download both input CSVs (input names have no {rank} — shared across all instances)
    cy_local = f"current_year_obs_r{rank}.csv"
    avg_local = f"ten_year_avg_r{rank}.csv"

    faasr_get_file(local_file=cy_local, remote_folder=folder, remote_file=input1)
    faasr_get_file(local_file=avg_local, remote_folder=folder, remote_file=input2)

    cy_df = pd.read_csv(cy_local)
    avg_df = pd.read_csv(avg_local)
    os.remove(cy_local)
    os.remove(avg_local)

    # Parse current-year dates and compute day_of_year for merging
    cy_df["date"] = pd.to_datetime(cy_df["date"])
    cy_df["day_of_year"] = cy_df["date"].dt.dayofyear

    # Merge on day_of_year so x-axis is aligned
    merged = cy_df.merge(avg_df[["day_of_year", avg_col]], on="day_of_year", how="left")

    current_year = cy_df["date"].dt.year.iloc[0]
    faasr_log(f"Plotting {len(merged)} data points for {var_label}, year {current_year}")

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        merged["date"],
        merged[obs_col],
        color="#1f77b4",
        linewidth=1.2,
        label=f"{current_year} Observed",
        zorder=3,
    )
    ax.plot(
        merged["date"],
        merged[avg_col],
        color="#ff7f0e",
        linewidth=1.5,
        linestyle="--",
        label="10-Year Average",
        zorder=2,
    )

    ax.set_title(f"Corvallis, OR — {var_label}: {current_year} vs. 10-Year Daily Average", fontsize=13)
    ax.set_xlabel("Date")
    ax.set_ylabel(y_label)
    ax.legend()
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()

    out_local = f"climate_variable_plot_{rank}.png"
    fig.savefig(out_local, dpi=150)
    plt.close(fig)

    remote_name = output1.replace("{rank}", str(rank))
    faasr_log(f"Uploading {remote_name}")
    faasr_put_file(local_file=out_local, remote_folder=folder, remote_file=remote_name)
    os.remove(out_local)

    faasr_log(f"plot_climate_variable rank {rank} complete")
