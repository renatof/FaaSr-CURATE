import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import geopandas as gpd
import contextily as ctx
from shapely.geometry import Point, box

# Oregon approximate bounding box (matches filter_oregon_records)
OR_LAT_MIN, OR_LAT_MAX = 42.0, 46.5
OR_LON_MIN, OR_LON_MAX = -124.6, -116.5

WGS84 = "EPSG:4326"
WEB_MERCATOR = "EPSG:3857"

def map_oregon_observations(folder: str, input1: str, output1: str) -> None:
    local_input = "castor_canadensis_oregon.csv"
    local_output = "castor_canadensis_oregon_map.png"

    faasr_get_file(local_file=local_input, remote_folder=folder, remote_file=input1)
    faasr_log(f"Downloaded '{input1}' from folder '{folder}'")

    df = pd.read_csv(local_input)
    faasr_log(f"Loaded {len(df)} Oregon records")

    df["decimalLatitude"] = pd.to_numeric(df["decimalLatitude"], errors="coerce")
    df["decimalLongitude"] = pd.to_numeric(df["decimalLongitude"], errors="coerce")
    df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])
    faasr_log(f"{len(df)} records have valid coordinates for plotting")

    # Build GeoDataFrame of observation points
    geometry = [Point(lon, lat) for lat, lon in
                zip(df["decimalLatitude"], df["decimalLongitude"])]
    gdf_points = gpd.GeoDataFrame(df, geometry=geometry, crs=WGS84)

    # Oregon bounding box as a polygon for the boundary overlay
    oregon_box = gpd.GeoDataFrame(
        geometry=[box(OR_LON_MIN, OR_LAT_MIN, OR_LON_MAX, OR_LAT_MAX)],
        crs=WGS84,
    )

    # Reproject to Web Mercator for contextily basemap tiles
    gdf_points_wm = gdf_points.to_crs(WEB_MERCATOR)
    oregon_box_wm = oregon_box.to_crs(WEB_MERCATOR)

    fig, ax = plt.subplots(figsize=(10, 8))

    # Draw Oregon bounding box boundary
    oregon_box_wm.boundary.plot(ax=ax, color="black", linewidth=1.5, label="Oregon boundary")

    # Plot observation points
    gdf_points_wm.plot(ax=ax, color="red", markersize=8, alpha=0.6, label="Castor canadensis")

    # Add OpenStreetMap basemap tiles
    try:
        ctx.add_basemap(ax, crs=WEB_MERCATOR, source=ctx.providers.OpenStreetMap.Mapnik, zoom="auto")
        faasr_log("Basemap tiles added successfully")
    except Exception as e:
        faasr_log(f"Basemap tiles unavailable ({e}); proceeding without basemap")

    ax.set_title(
        "Castor canadensis Observations in Oregon\n"
        f"(n={len(gdf_points)} records; GBIF data)",
        fontsize=14,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    handles = [
        mpatches.Patch(edgecolor="black", facecolor="none", label="Oregon bounding box"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="red",
                   markersize=8, alpha=0.6, label="Castor canadensis"),
    ]
    ax.legend(handles=handles, loc="lower right")

    plt.tight_layout()
    fig.savefig(local_output, dpi=150, bbox_inches="tight")
    plt.close(fig)
    faasr_log(f"Saved map to '{local_output}'")

    faasr_put_file(local_file=local_output, remote_folder=folder, remote_file=output1)
    faasr_log(f"Uploaded '{output1}' to folder '{folder}'")

    os.remove(local_input)
    os.remove(local_output)
