def plot_tmax_regression(folder: str, input1: str, input2: str, input3: str, output1: str) -> None:
    import os
    import datetime
    import tempfile
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    with tempfile.TemporaryDirectory() as tmpdir:
        local_current  = os.path.join(tmpdir, "current.csv")
        local_fitted   = os.path.join(tmpdir, "fitted.csv")
        local_summary  = os.path.join(tmpdir, "summary.csv")

        faasr_get_file(local_file=local_current,  remote_folder=folder, remote_file=input1)
        faasr_get_file(local_file=local_fitted,   remote_folder=folder, remote_file=input2)
        faasr_get_file(local_file=local_summary,  remote_folder=folder, remote_file=input3)

        obs = pd.read_csv(local_current, parse_dates=["date"])
        obs = obs.dropna(subset=["TMAX"])
        obs["day_of_year"] = obs["date"].dt.dayofyear
        obs["month"]       = obs["date"].dt.month

        fitted  = pd.read_csv(local_fitted)
        summary = pd.read_csv(local_summary)

        slope     = float(summary["slope"].iloc[0])
        intercept = float(summary["intercept"].iloc[0])
        r_value   = float(summary["r_value"].iloc[0])
        r2        = r_value ** 2

        current_year = obs["date"].dt.year.iloc[0]
        faasr_log(f"Plotting TMAX regression for {current_year}: slope={slope:.4f}, intercept={intercept:.4f}, r2={r2:.4f}")

        # Qualitative colormap — one colour per calendar month (1–12)
        MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        cmap = matplotlib.colormaps["tab20"].resampled(12)
        month_colors = {m: cmap(m - 1) for m in range(1, 13)}

        fig, ax = plt.subplots(figsize=(14, 5))

        # Scatter: one series per month so legend shows month labels
        for month in sorted(obs["month"].unique()):
            mask = obs["month"] == month
            ax.scatter(
                obs.loc[mask, "day_of_year"],
                obs.loc[mask, "TMAX"],
                color=month_colors[month],
                s=30,
                alpha=0.85,
                label=MONTH_ABBR[month - 1],
                zorder=3,
            )

        # OLS regression line in red
        eq_label = (
            f"TMAX = {slope:.2f}·DOY + {intercept:.2f}"
            f"\n$R^2$ = {r2:.4f}"
        )
        ax.plot(
            fitted["day_of_year"],
            fitted["TMAX_fitted"],
            color="red",
            linewidth=2.0,
            label=eq_label,
            zorder=4,
        )

        # X-axis: month abbreviations at the first DOY of each month
        doy_set = set(obs["day_of_year"].values)
        month_ticks  = []
        month_labels = []
        for m in range(1, 13):
            try:
                d = datetime.date(current_year, m, 1)
                doy = d.timetuple().tm_yday
                if doy in doy_set or m == obs["month"].min():
                    month_ticks.append(doy)
                    month_labels.append(d.strftime("%b"))
            except ValueError:
                pass
        ax.set_xticks(month_ticks)
        ax.set_xticklabels(month_labels, fontsize=9)

        ax.set_xlabel("Month", fontsize=11)
        ax.set_ylabel("Max Temperature (°C)", fontsize=11)
        ax.set_title(f"Corvallis OR — TMAX Linear Regression: {current_year}", fontsize=13)

        ax.grid(which="both", linestyle=":", alpha=0.4)

        ax.legend(fontsize=9, ncol=2, loc="upper left")
        fig.tight_layout()

        local_png = os.path.join(tmpdir, output1)
        fig.savefig(local_png, dpi=150, bbox_inches="tight")
        plt.close(fig)

        faasr_log(f"Uploading {output1}")
        faasr_put_file(local_file=local_png, remote_folder=folder, remote_file=output1)

    faasr_log("plot_tmax_regression complete")
