import polars as pl
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import sys
import os
PROJECT_DIR = sys.prefix
CONVEYOR_FILE = os.path.join(PROJECT_DIR, 'data', 'conveyor_sst.csv')


def main():
    os.chdir(PROJECT_DIR)

    conveyor = pl.read_csv(CONVEYOR_FILE)

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson(70))
    ax.set_global()
    ax.coastlines()

    # Conveyor data is in two paths - draw separately
    for i in range(2):
        path = conveyor.filter(pl.col('path') == i+1)
        ax.plot(
            path['longitude'],
            path['latitude'],
            linewidth=5,
            color='black',
            transform=ccrs.Geodetic()
        )

    plt.savefig(
        os.path.join(PROJECT_DIR, 'figs', 'conveyor_path.png')
    )


if __name__ == '__main__':
    main()
