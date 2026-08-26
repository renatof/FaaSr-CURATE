def generate_climate_plot(folder: str, input1: str, input2: str, output1: str) -> None:
    import os
    import tempfile
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    r = faasr_rank()
    rank = r["rank"]

    # rank → variable assignment per spec
    RANK_CONFIG = {
        1: {"col": "PRCP", "label": "Precipitation (mm)", "title": "Daily Precipitation", "kind": "bar"},
        2: {"col": "TMAX", "label": "Max Temperature (°C)", "title": "Daily Maximum Temperature", "kind": "line"},
        3: {"col": "TMIN", "label": "Min Temperature (°C)", "title": "Daily Minimum Temperature", "kind": "line"},
    }
    if rank not in RANK_CONFIG:
        msg = f"Unexpected rank {rank}; expected 1, 2, or 3"
        faasr_log(f"ERROR: {msg}")
        raise RuntimeError(msg)

    cfg = RANK_CONFIG[rank]
    col = cfg["col"]
    faasr_log(f"Rank {rank}: plotting {col}")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_current = os.path.join(tmpdir, "current.csv")
        local_avg = os.path.join(tmpdir, "avg.csv")

        faasr_get_file(local_file=local_current, remote_folder=folder, remote_file=input1)
        faasr_get_file(local_file=local_avg, remote_folder=folder, remote_file=input2)

        current = pd.read_csv(local_current)
        avg = pd.read_csv(local_avg)

        current["date"] = pd.to_datetime(current["date"])
        current["day_of_year"] = current["date"].dt.dayofyear

        # Align 10yr average to current-year day-of-year range
        doy_range = current["day_of_year"].values
        avg_aligned = avg[avg["day_of_year"].isin(doy_range)].copy()

        # Merge so x-axis is consistent
        merged = pd.merge(
            current[["day_of_year", "date", col]],
            avg_aligned[["day_of_year", col]].rename(columns={col: f"{col}_avg"}),
            on="day_of_year",
            how="left",
        )
        merged = merged.sort_values("day_of_year")

        fig, ax = plt.subplots(figsize=(14, 5))

        x = merged["day_of_year"].values
        y_current = merged[col].values
        y_avg = merged[f"{col}_avg"].values

        if cfg["kind"] == "bar":
            # Precipitation: grouped bars
            width = 0.4
            ax.bar(x - width / 2, y_current, width=width, color="#2196F3", alpha=0.8, label=f"{col} (current year)")
            ax.bar(x + width / 2, y_avg, width=width, color="#FF9800", alpha=0.7, label="10-yr average")
        else:
            # Temperature: lines with shaded uncertainty band
            ax.plot(x, y_current, color="#E53935", linewidth=1.2, label=f"{col} (current year)")
            ax.plot(x, y_avg, color="#1E88E5", linewidth=1.2, linestyle="--", label="10-yr average")
            ax.fill_between(x, y_current, y_avg, alpha=0.12, color="#888888")

        # X-axis: label with month ticks
        current_year = merged["date"].dt.year.iloc[0]
        import datetime
        month_doys = []
        month_labels = []
        for month in range(1, 13):
            try:
                d = datetime.date(current_year, month, 1)
                doy = d.timetuple().tm_yday
                if doy in set(x):
                    month_doys.append(doy)
                    month_labels.append(d.strftime("%b"))
            except ValueError:
                pass
        ax.set_xticks(month_doys)
        ax.set_xticklabels(month_labels, fontsize=9)
        ax.xaxis.set_minor_locator(mticker.AutoMinorLocator())

        ax.set_xlabel("Month", fontsize=11)
        ax.set_ylabel(cfg["label"], fontsize=11)
        ax.set_title(f"Corvallis OR — {cfg['title']}: {current_year} vs 10-Year Average", fontsize=13)
        ax.legend(fontsize=10)
        ax.grid(axis="y", linestyle=":", alpha=0.5)
        fig.tight_layout()

        local_png = os.path.join(tmpdir, "plot.png")
        fig.savefig(local_png, dpi=150, bbox_inches="tight")
        plt.close(fig)

        remote_png = output1.replace("{rank}", str(rank))
        faasr_log(f"Uploading {remote_png}")
        faasr_put_file(local_file=local_png, remote_folder=folder, remote_file=remote_png)

    faasr_log(f"generate_climate_plot rank {rank} ({col}) complete")
