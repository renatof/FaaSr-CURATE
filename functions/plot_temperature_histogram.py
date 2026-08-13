import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tempfile
import os

def plot_temperature_histogram(folder: str, input1: str, output1: str) -> None:
    faasr_log(f"Downloading {input1} from folder {folder}")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_csv = os.path.join(tmpdir, input1)
        faasr_get_file(local_file=local_csv, remote_folder=folder, remote_file=input1)

        df = pd.read_csv(local_csv)
        if "temperature" not in df.columns:
            raise ValueError(f"Expected column 'temperature' in {input1}, got: {list(df.columns)}")

        faasr_log("Generating temperature histogram")
        fig, ax = plt.subplots()
        ax.hist(df["temperature"], bins=30)
        ax.set_xlabel("Temperature (degrees F)")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of Temperature Values")

        local_png = os.path.join(tmpdir, output1)
        fig.savefig(local_png)
        plt.close(fig)

        faasr_log(f"Uploading {output1} to folder {folder}")
        faasr_put_file(local_file=local_png, remote_folder=folder, remote_file=output1)

    faasr_log("plot_temperature_histogram complete")
