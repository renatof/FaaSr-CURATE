import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


def plot_weather_comparisons(
    folder: str,
    input1: str,
    input2: str,
    output1: str,
    output2: str,
    output3: str,
) -> None:
    r = faasr_rank()
    rank = r["rank"]
    faasr_log(f"plot_weather_comparisons rank={rank}")

    # Rank 1 → precipitation, 2 → TMAX, 3 → TMIN
    plot_configs = {
        1: {
            "col": "PRCP",
            "title": "Corvallis OR — Daily Precipitation: Current Year vs 10-Year Average",
            "ylabel": "Precipitation (mm)",
            "output": output1,
            "cur_label": "2026 Precipitation",
            "avg_label": "10-Year Average Precipitation",
            "cur_color": "#1f77b4",
            "avg_color": "#ff7f0e",
        },
        2: {
            "col": "TMAX",
            "title": "Corvallis OR — Daily Max Temperature: Current Year vs 10-Year Average",
            "ylabel": "Max Temperature (°C)",
            "output": output2,
            "cur_label": "2026 TMAX",
            "avg_label": "10-Year Average TMAX",
            "cur_color": "#d62728",
            "avg_color": "#ff9896",
        },
        3: {
            "col": "TMIN",
            "title": "Corvallis OR — Daily Min Temperature: Current Year vs 10-Year Average",
            "ylabel": "Min Temperature (°C)",
            "output": output3,
            "cur_label": "2026 TMIN",
            "avg_label": "10-Year Average TMIN",
            "cur_color": "#2ca02c",
            "avg_color": "#98df8a",
        },
    }

    cfg = plot_configs[rank]

    with tempfile.TemporaryDirectory() as tmpdir:
        cur_path = os.path.join(tmpdir, "current.csv")
        avg_path = os.path.join(tmpdir, "avg.csv")

        faasr_get_file(local_file=cur_path, remote_folder=folder, remote_file=input1)
        faasr_get_file(local_file=avg_path, remote_folder=folder, remote_file=input2)

        df_cur = pd.read_csv(cur_path, parse_dates=["date"])
        df_avg = pd.read_csv(avg_path)

        col = cfg["col"]
        if col not in df_cur.columns:
            raise ValueError(f"Column '{col}' missing from current-year CSV")
        if col not in df_avg.columns:
            raise ValueError(f"Column '{col}' missing from 10-year-average CSV")

        # Build average series aligned to current year's dates by MM-DD key
        df_avg["mm_dd"] = df_avg["date"].astype(str).str.strip()
        avg_map = df_avg.set_index("mm_dd")[col]

        df_cur["mm_dd"] = df_cur["date"].dt.strftime("%m-%d")
        df_cur_avg_vals = df_cur["mm_dd"].map(avg_map)

        fig, ax = plt.subplots(figsize=(14, 5))

        ax.plot(
            df_cur["date"],
            df_cur[col],
            color=cfg["cur_color"],
            linewidth=1.2,
            label=cfg["cur_label"],
        )
        ax.plot(
            df_cur["date"],
            df_cur_avg_vals,
            color=cfg["avg_color"],
            linewidth=1.2,
            linestyle="--",
            label=cfg["avg_label"],
        )

        ax.set_title(cfg["title"], fontsize=13, fontweight="bold")
        ax.set_xlabel("Date")
        ax.set_ylabel(cfg["ylabel"])
        ax.legend(loc="upper right")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        fig.autofmt_xdate()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        out_filename = cfg["output"].replace("{rank}", str(rank))
        out_path = os.path.join(tmpdir, f"plot_{rank}.png")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        faasr_log(f"Saved plot to {out_filename}")

        faasr_put_file(local_file=out_path, remote_folder=folder, remote_file=out_filename)

    faasr_log(f"plot_weather_comparisons rank={rank} complete")
