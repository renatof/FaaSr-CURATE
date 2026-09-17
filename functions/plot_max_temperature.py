import os
import tempfile
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot_max_temperature(folder: str, input1: str, input2: str, output1: str) -> None:
    # ── Load inputs ───────────────────────────────────────────────────────────
    cy_local = tempfile.mktemp(suffix=".csv")
    avg_local = tempfile.mktemp(suffix=".csv")
    faasr_get_file(local_file=cy_local, remote_folder=folder, remote_file=input1)
    faasr_get_file(local_file=avg_local, remote_folder=folder, remote_file=input2)

    cy_df = pd.read_csv(cy_local)
    avg_df = pd.read_csv(avg_local)
    os.unlink(cy_local)
    os.unlink(avg_local)

    # ── Validate expected columns ─────────────────────────────────────────────
    for col in ("date", "TMAX"):
        if col not in cy_df.columns:
            raise ValueError(f"Current-year CSV missing column: {col}")
    for col in ("day_of_year", "TMAX_avg"):
        if col not in avg_df.columns:
            raise ValueError(f"10-year average CSV missing column: {col}")

    cy_df["date"] = pd.to_datetime(cy_df["date"])

    # ── Map 10-year avg day_of_year to calendar dates in the current year ─────
    current_year = int(cy_df["date"].dt.year.iloc[0])
    avg_dates = pd.to_datetime(
        avg_df["day_of_year"].apply(lambda d: f"{current_year}-{d:03d}"),
        format="%Y-%j",
        errors="coerce",
    )

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        cy_df["date"],
        cy_df["TMAX"],
        color="#1f77b4",
        linewidth=1.5,
        label=f"{current_year} Daily Max Temperature",
    )
    ax.plot(
        avg_dates,
        avg_df["TMAX_avg"],
        color="#d62728",
        linewidth=1.8,
        linestyle="--",
        label="10-Year Daily Average Max Temperature",
    )

    ax.set_title(
        "Corvallis, OR — Daily Maximum Temperature: Current Year vs. 10-Year Average",
        fontsize=13,
        pad=12,
    )
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Maximum Temperature (°F)", fontsize=11)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "plot.png")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        faasr_put_file(local_file=out_path, remote_folder=folder, remote_file=output1)

    faasr_log(f"Max temperature comparison plot saved as {output1}")
