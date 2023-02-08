import numpy as np
import polars as pl
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import sys
import os
from typing import Tuple
from math import atan2, cos, sin, sqrt


PROJECT_DIR = sys.prefix
DATA_FILE = os.path.join(PROJECT_DIR, 'data', 'conveyor_sst.csv')
OUTDIR = os.path.join(PROJECT_DIR, 'figs', 'sst_frames')
YEARS = [str(y) for y in range(1982, 2022)]
PATH_FILE = pl.read_csv(DATA_FILE)

# Get differences since 1982
PATH_SST = (
    PATH_FILE
    .with_columns([
        (pl.col(y) - pl.col(YEARS[0])).alias(y) for y in YEARS[1:]
    ] + [pl.lit(0).alias(YEARS[0])]
    )
)
# print(PATH_SST)
MAXABS = max(
    PATH_SST
    .select([
        pl.col(y).abs().alias(y) for y in YEARS
    ])
    .max()
    .row(0)
)
NORM = plt.Normalize(-MAXABS, MAXABS)
CMAP = plt.colormaps['RdBu_r']
LWIDTH = 7


# Need to think about midpoint generation
def midpoint(lon0: int, lon1: int, lat0: int, lat1: int) -> Tuple[float, float]:
    dlon = np.deg2rad(lon1 - lon0)

    lat0 = np.deg2rad(lat0)
    lat1 = np.deg2rad(lat1)
    lon0 = np.deg2rad(lon0)
    # lon1 = np.deg2rad(lon1)

    Bx = cos(lat1) * cos(dlon)
    By = cos(lat1) * sin(dlon)
    lat2 = atan2(sin(lat0) + sin(lat1), sqrt((cos(lat0)+Bx)**2 + By**2))
    lon2 = lon0 + atan2(By, cos(lat0) + Bx)

    return (np.rad2deg(lon2), np.rad2deg(lat2))


def draw_segment(path, year, i, ax):
    num_path_points = len(path)
    beforelon, beforelat = midpoint(
        path['longitude'][(i-1) % num_path_points],
        path['longitude'][(i) % num_path_points],
        path['latitude'][(i-1) % num_path_points],
        path['latitude'][(i) % num_path_points],
    )
    afterlon, afterlat = midpoint(
        path['longitude'][(i+1) % num_path_points],
        path['longitude'][(i) % num_path_points],
        path['latitude'][(i+1) % num_path_points],
        path['latitude'][(i) % num_path_points],
    )
    lons = [
        beforelon,
        path['longitude'][i],
        afterlon,
    ]
    lats = [
        beforelat,
        path['latitude'][i],
        afterlat,
    ]
    temp_diff = path[year][i]

    ax.plot(
        lons,
        lats,
        linewidth=LWIDTH,
        color=CMAP(NORM(temp_diff)),
        transform=ccrs.Geodetic()
    )


def year_frame(year: str):
    plt.close()
    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()
    ax.coastlines()

    # Draw background line
    for i in range(2):
        path = PATH_SST.filter(pl.col('path') == i+1)
        ax.plot(
            path['longitude'],
            path['latitude'],
            linewidth=LWIDTH+4,
            color='black',
            transform=ccrs.Geodetic()
        )

    # Handle path 1
    # End points are not part of loop
    path1 = PATH_SST.filter(pl.col('path') == 1)

    # Handle end-points
    _, lon0, lat0, *_ = path1.row(0)
    _, lon1, lat1, *_ = path1.row(1)
    _, lonend, latend, *_ = path1.row(-1)
    _, lonprev, latprev, *_ = path1.row(-2)

    lon01, lat01 = midpoint(lon0, lon1, lat0, lat1)
    lonendmid, latendmid = midpoint(lonend, lonprev, latend, latprev)
    ax.plot(
        [lon0, lon01],
        [lat0, lat01],
        linewidth=LWIDTH,
        color=CMAP(NORM(path1[year][0])),
        transform=ccrs.Geodetic(),
    )
    ax.plot(
        [lonend, lonendmid],
        [latend, latendmid],
        linewidth=LWIDTH,
        color=CMAP(NORM(path1[year][-1])),
        transform=ccrs.Geodetic(),
    )

    # Handle non-end points
    for i in range(1, len(path1)-1):
        draw_segment(path1, year, i, ax)

    # Handle Path 2 - Can use mod!
    path2 = PATH_SST.filter(pl.col('path') == 2)
    for i in range(len(path2)):
        draw_segment(path2, year, i, ax)

    fig.colorbar(plt.cm.ScalarMappable(norm=NORM, cmap=CMAP),
                 ax=ax, label='Change in SST (°C)')

    gl = ax.gridlines(draw_labels=True)
    gl.top_labels = False
    gl.right_labels = False
    ax.set_title(year)
    fig.suptitle('SST Difference Along Broecker\'s Ocean Conveyor Since 1982')
    plt.savefig(os.path.join(OUTDIR, f'{year}.png'))


def main():
    os.chdir(PROJECT_DIR)

    for year in YEARS:
        year_frame(year)


if __name__ == '__main__':
    main()
