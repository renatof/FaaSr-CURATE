import os
import time
import zipfile
import shutil
import tempfile
import glob
import pandas as pd
from pygbif import occurrences as occ


def download_gbif_records(folder: str, output1: str) -> None:
    gbif_user = faasr_secret("GBIF_USER")
    gbif_pwd = faasr_secret("GBIF_PWD")
    gbif_email = faasr_secret("GBIF_EMAIL")

    local_file = "castor_canadensis_raw.csv"

    faasr_log("Submitting GBIF bulk download request for Castor canadensis in Oregon")

    res = occ.download(
        ["scientificName = 'Castor canadensis'", "stateProvince = 'Oregon'"],
        user=gbif_user,
        pwd=gbif_pwd,
        email=gbif_email,
    )
    download_key = res[0]
    faasr_log(f"Download request submitted. Key: {download_key}")

    # Poll until SUCCEEDED or FAILED, logging every iteration
    while True:
        meta = occ.download_meta(download_key)
        status = meta.get("status", "UNKNOWN")
        faasr_log(f"Download status: {status}")
        if status == "SUCCEEDED":
            break
        if status == "FAILED":
            msg = f"GBIF bulk download failed. Key: {download_key}"
            faasr_log(msg)
            raise RuntimeError(msg)
        time.sleep(10)

    faasr_log("Retrieving zip file from GBIF")
    tmpdir = tempfile.mkdtemp()
    try:
        result = occ.download_get(download_key, path=tmpdir)
        zip_path = result["path"]

        faasr_log(f"Extracting zip: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmpdir)

        # DarwinCore Archive uses tab-separated occurrence.txt
        occurrence_file = os.path.join(tmpdir, "occurrence.txt")
        if not os.path.exists(occurrence_file):
            candidates = (
                glob.glob(os.path.join(tmpdir, "*.csv"))
                + glob.glob(os.path.join(tmpdir, "*.txt"))
            )
            candidates = [f for f in candidates if f != zip_path]
            if not candidates:
                msg = "No occurrence file found in GBIF download zip"
                faasr_log(msg)
                raise RuntimeError(msg)
            occurrence_file = candidates[0]

        faasr_log(f"Reading occurrence data from {os.path.basename(occurrence_file)}")
        df = pd.read_csv(occurrence_file, sep="\t", low_memory=False, on_bad_lines="skip")

        faasr_log(f"Downloaded {len(df)} records with {len(df.columns)} columns")
        df.to_csv(local_file, index=False)
        faasr_log(f"Wrote {len(df)} rows to {local_file}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    faasr_put_file(local_file=local_file, remote_folder=folder, remote_file=output1)
    faasr_log(f"Uploaded '{output1}' to folder '{folder}'")

    os.remove(local_file)
