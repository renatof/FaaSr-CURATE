def create_climate_plot(folder: str, input1: str, input2: str, output1: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd
    from datetime import datetime
    import os

    r = faasr_rank()
    rank = r["rank"]
    faasr_log(f"create_climate_plot rank={rank}/3")

    # Resolve filenames — substitute {rank} if present
    in1 = input1.format(rank=rank)
    in2 = input2.format(rank=rank)
    out1 = output1.format(rank=rank)

    # Download CSVs
    local_curr = f"/tmp/current_year_weather_{rank}.csv"
    local_avg  = f"/tmp/ten_year_avg_weather_{rank}.csv"
    faasr_get_file(local_file=local_curr, remote_folder=folder, remote_file=in1)
    faasr_get_file(local_file=local_avg,  remote_folder=folder, remote_file=in2)

    curr_df = pd.read_csv(local_curr, parse_dates=["date"])
    avg_df  = pd.read_csv(local_avg)

    os.remove(local_curr)
    os.remove(local_avg)

    # Map rank → variable names and plot labels
    config = {
        1: dict(curr_col="PRCP",  avg_col="PRCP_avg",  label="Precipitation (mm)",
                title="Daily Precipitation: Current Year vs 10-Year Average",
                plot_type="bar",  color_curr="#1f77b4", color_avg="#ff7f0e"),
        2: dict(curr_col="TMAX",  avg_col="TMAX_avg",  label="Max Temperature (°C)",
                title="Daily Max Temperature: Current Year vs 10-Year Average",
                plot_type="line", color_curr="#d62728", color_avg="#aec7e8"),
        3: dict(curr_col="TMIN",  avg_col="TMIN_avg",  label="Min Temperature (°C)",
                title="Daily Min Temperature: Current Year vs 10-Year Average",
                plot_type="line", color_curr="#1f77b4", color_avg="#ffbb78"),
    }
    if rank not in config:
        msg = f"Unexpected rank {rank}; expected 1, 2, or 3"
        faasr_log(f"ERROR: {msg}")
        raise ValueError(msg)
    cfg = config[rank]

    # Merge current-year data with 10-year averages on (month, day)
    curr_df = curr_df.dropna(subset=["date"])
    curr_df["month"] = curr_df["date"].dt.month
    curr_df["day"]   = curr_df["date"].dt.day
    merged = curr_df.merge(avg_df[["month", "day", cfg["avg_col"]]],
                           on=["month", "day"], how="left")
    merged = merged.sort_values("date").reset_index(drop=True)

    dates     = merged["date"]
    curr_vals = pd.to_numeric(merged[cfg["curr_col"]], errors="coerce")
    avg_vals  = pd.to_numeric(merged[cfg["avg_col"]],  errors="coerce")

    fig, ax = plt.subplots(figsize=(14, 5))

    if cfg["plot_type"] == "bar":
        width = 0.4
        x = range(len(dates))
        ax.bar([i - width / 2 for i in x], curr_vals,
               width=width, label="Current Year", color=cfg["color_curr"], alpha=0.85)
        ax.bar([i + width / 2 for i in x], avg_vals,
               width=width, label="10-Year Average", color=cfg["color_avg"], alpha=0.85)
        # Show month boundaries as tick labels instead of every date
        month_ticks = []
        month_labels = []
        prev_m = None
        for i, d in enumerate(dates):
            m = d.month
            if m != prev_m:
                month_ticks.append(i)
                month_labels.append(d.strftime("%b"))
                prev_m = m
        ax.set_xticks(month_ticks)
        ax.set_xticklabels(month_labels)
    else:
        ax.plot(dates, curr_vals, label="Current Year",
                color=cfg["color_curr"], linewidth=1.5)
        ax.plot(dates, avg_vals,  label="10-Year Average",
                color=cfg["color_avg"], linewidth=1.5, linestyle="--")
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        fig.autofmt_xdate()

    ax.set_title(cfg["title"], fontsize=13)
    ax.set_ylabel(cfg["label"])
    ax.set_xlabel("Month")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    local_png = f"/tmp/{out1}"
    plt.savefig(local_png, dpi=150)
    plt.close(fig)
    faasr_log(f"Plot saved: {out1}")

    faasr_put_file(local_file=local_png, remote_folder=folder, remote_file=out1)
    os.remove(local_png)
    faasr_log(f"create_climate_plot rank={rank} complete")
