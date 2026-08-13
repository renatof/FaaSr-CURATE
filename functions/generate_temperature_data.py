import numpy as np
import pandas as pd
import tempfile
import os

def generate_temperature_data(folder: str, output1: str) -> None:
    faasr_log("Generating 1000 Gaussian-sampled temperature values (mean=70F, std=10F)")

    rng = np.random.default_rng()
    temperatures = rng.normal(loc=70.0, scale=10.0, size=1000)

    df = pd.DataFrame({"temperature": temperatures})

    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = os.path.join(tmpdir, output1)
        df.to_csv(local_path, index=False)
        faasr_log(f"Uploading {output1} to folder {folder}")
        faasr_put_file(local_file=local_path, remote_folder=folder, remote_file=output1)

    faasr_log("generate_temperature_data complete")
