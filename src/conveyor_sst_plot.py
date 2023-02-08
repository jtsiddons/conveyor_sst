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


# Need to think about midpoint generation
def midpoint(lon0: int, lon1: int, lat0: int, lat1: int) -> Tuple[float, float]:
    theta0 = np.deg2rad(lat0)
    theta1 = np.deg2rad(lat1)
    phi0 = np.deg2rad(lon0)
    phi1 = np.deg2rad(lon1)

    dlon = np.deg2rad(lon1 - lon0)

    dx = cos(theta1) * cos(dlon)
    dy = cos(theta1) * sin(dlon)

    theta_mid = atan2(sin(theta0) + sin(theta1),
                      sqrt((cos(theta0) + dx)*(cos(theta1) + dx) + dy**2))
    phi_mid = phi0 + atan2(dy, cos(theta0) + dx)
    return (np.rad2deg(phi_mid), np.rad2deg(theta_mid))


def year_frame(year: str, path_sst: pl.DataFrame, maxabs: float):
    plt.close()
    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()
    ax.coastlines()

    # Draw background line
    for i in range(2):
        path = path_sst.filter(pl.col('path') == i+1)
        ax.plot(
            path['longitude'],
            path['latitude'],
            linewidth=11,
            color='black',
            transform=ccrs.Geodetic()
        )

    norm = plt.Normalize(-maxabs, maxabs)
    cmap = plt.colormaps['RdBu_r']
    lwidth = 7

    # Handle path 1
    # End points are not part of loop
    path1 = path_sst.filter(pl.col('path') == 1)

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
        linewidth=lwidth,
        color=cmap(norm(path1[year][0])),
        transform=ccrs.Geodetic(),
    )
    ax.plot(
        [lonend, lonendmid],
        [latend, latendmid],
        linewidth=lwidth,
        color=cmap(norm(path1[year][-1])),
        transform=ccrs.Geodetic(),
    )

    # Handle non-end points
    for i in range(1, len(path1)-1):
        beforelon, beforelat = midpoint(
            path1['longitude'][i-1],
            path1['longitude'][i],
            path1['latitude'][i-1],
            path1['latitude'][i],
        )
        afterlon, afterlat = midpoint(
            path1['longitude'][i+1],
            path1['longitude'][i],
            path1['latitude'][i+1],
            path1['latitude'][i],
        )
        lons = [
            beforelon,
            path1['longitude'][i],
            afterlon,
        ]
        lats = [
            beforelat,
            path1['latitude'][i],
            afterlat,
        ]
        temp_diff = path1[year][i]

        ax.plot(
            lons,
            lats,
            linewidth=8,
            color=cmap(norm(path1[year][i])),
            transform=ccrs.Geodetic()
        )

        # Handle Path 2 - Can use mod!
    path2 = path_sst.filter(pl.col('path') == 2)
    l = len(path2)
    for i in range(l):
        beforelon, beforelat = midpoint(
            path2['longitude'][(i-1) % l],
            path2['longitude'][(i) % l],
            path2['latitude'][(i-1) % l],
            path2['latitude'][(i) % l],
        )
        afterlon, afterlat = midpoint(
            path2['longitude'][(i+1) % l],
            path2['longitude'][(i) % l],
            path2['latitude'][(i+1) % l],
            path2['latitude'][(i) % l],
        )
        lons = [
            beforelon,
            path2['longitude'][i],
            afterlon,
        ]
        lats = [
            beforelat,
            path2['latitude'][i],
            afterlat,
        ]
        temp_diff = path2[year][i]

        ax.plot(
            lons,
            lats,
            linewidth=8,
            color=cmap(norm(path2[year][i])),
            transform=ccrs.Geodetic()
        )

    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap),
                 ax=ax, label='Change in SST (°C)')

    gl = ax.gridlines(draw_labels=True)
    gl.top_labels = False
    gl.right_labels = False
    ax.set_title(year)
    fig.suptitle('SST Difference Along Broecker\'s Ocean Conveyor Since 1982')
    plt.savefig(os.path.join(OUTDIR, f'{year}.png'))


def main():
    os.chdir(PROJECT_DIR)

    path_sst = pl.read_csv(DATA_FILE)

    # Get differences since 1982
    path_sst = (
        path_sst
        .with_columns([
            (pl.col(y) - pl.col(path_sst.columns[3])).alias(y) for y in path_sst.columns[4:]
        ] + [pl.lit(0).alias(path_sst.columns[3])]
        )
    )
    print(path_sst)

    # Get absolute maximum change since 1982 - for colouring.
    years = path_sst.columns[3:]
    maxabs = max(
        path_sst
        .select([
            pl.col(y).abs().alias(y) for y in years
        ])
        .max()
        .row(0)
    )

    for year in years:
        year_frame(year, path_sst, maxabs)


if __name__ == '__main__':
    main()
