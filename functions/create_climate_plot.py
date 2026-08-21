def create_climate_plot(folder: str, input1: str, input2: str, output1: str) -> None:
    import os
    import tempfile
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd
    from datetime import datetime

    r = faasr_rank()
    rank = r['rank']

    # Rank→variable mapping
    var_map = {1: 'PRCP', 2: 'TMAX', 3: 'TMIN'}
    title_map = {
        1: 'Precipitation — Corvallis OR: Current Year vs. 10-Year Average',
        2: 'Maximum Temperature — Corvallis OR: Current Year vs. 10-Year Average',
        3: 'Minimum Temperature — Corvallis OR: Current Year vs. 10-Year Average',
    }
    ylabel_map = {1: 'Precipitation (inches)', 2: 'Temperature (°F)', 3: 'Temperature (°F)'}
    cur_label_map = {1: 'Current Year', 2: 'Current Year', 3: 'Current Year'}
    avg_label_map = {1: '10-Year Average', 2: '10-Year Average', 3: '10-Year Average'}

    col = var_map[rank]

    # Inputs have no {rank} placeholder; output does
    out_file = output1.replace('{rank}', str(rank))

    faasr_log(f"Rank {rank}: plotting {col} → {out_file}")

    # Load current-year data
    cur_local = tempfile.mktemp(suffix='_current.csv')
    faasr_get_file(local_file=cur_local, remote_folder=folder, remote_file=input1)
    df_cur = pd.read_csv(cur_local)
    os.unlink(cur_local)

    df_cur['date'] = pd.to_datetime(df_cur['date'])
    df_cur = df_cur.sort_values('date').reset_index(drop=True)

    # Load 10-year average data
    avg_local = tempfile.mktemp(suffix='_avg.csv')
    faasr_get_file(local_file=avg_local, remote_folder=folder, remote_file=input2)
    df_avg = pd.read_csv(avg_local)
    os.unlink(avg_local)

    # Build current-year dates for the average by attaching the current year
    cur_year = df_cur['date'].dt.year.iloc[0]
    df_avg['month_day'] = df_avg['date'].astype(str)

    def md_to_date(md, year):
        try:
            return datetime.strptime(f"{year}-{md}", "%Y-%m-%d")
        except ValueError:
            # Feb 29 in non-leap years — skip
            return None

    df_avg['plot_date'] = df_avg['month_day'].apply(lambda md: md_to_date(md, cur_year))
    df_avg = df_avg.dropna(subset=['plot_date'])
    df_avg['plot_date'] = pd.to_datetime(df_avg['plot_date'])

    # Align: join average to current-year dates on MM-DD
    df_cur['month_day'] = df_cur['date'].dt.strftime('%m-%d')
    df_merged = df_cur[['date', 'month_day', col]].merge(
        df_avg[['month_day', col]].rename(columns={col: col + '_avg'}),
        on='month_day',
        how='left',
    )

    dates = df_merged['date']
    cur_vals = df_merged[col].astype(float)
    avg_vals = df_merged[col + '_avg'].astype(float)

    # Plot
    fig, ax = plt.subplots(figsize=(14, 5))

    if rank == 1:
        # Precipitation: bars for current year, line for average
        bar_width = 0.8
        ax.bar(dates, cur_vals, width=bar_width, color='steelblue', alpha=0.7,
               label=cur_label_map[rank], zorder=2)
        ax.plot(dates, avg_vals, color='darkorange', linewidth=1.8,
                label=avg_label_map[rank], zorder=3)
    else:
        # Temperature: lines for both
        ax.plot(dates, cur_vals, color='steelblue', linewidth=1.5,
                label=cur_label_map[rank], zorder=3)
        ax.plot(dates, avg_vals, color='darkorange', linewidth=1.8,
                linestyle='--', label=avg_label_map[rank], zorder=2)

    ax.set_title(title_map[rank], fontsize=13, fontweight='bold', pad=10)
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel(ylabel_map[rank], fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4, zorder=1)

    # x-axis: month ticks
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=30, ha='right')

    ax.set_xlim(dates.min(), dates.max())

    plt.tight_layout()

    fd, plot_tmp = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    try:
        fig.savefig(plot_tmp, dpi=150, bbox_inches='tight')
        plt.close(fig)
        faasr_log(f"Uploading {out_file}...")
        faasr_put_file(local_file=plot_tmp, remote_folder=folder, remote_file=out_file)
        faasr_log(f"create_climate_plot rank {rank} complete")
    finally:
        os.unlink(plot_tmp)
