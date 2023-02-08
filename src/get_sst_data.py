import pycmap
import polars as pl
import sys
import os


PROJECT_DIR = sys.prefix
API_FILE = os.path.join(PROJECT_DIR, 'data', 'api_key.csv')
CONVEYOR_PATH_FILE = os.path.join(PROJECT_DIR, 'data', 'conveyor.csv')
API_KEY = pl.read_csv(API_FILE)['apiKey'][0]
API = pycmap.API(token=API_KEY)
TABLE = API.search_catalog('satellite sst').iloc[0]
OUTFILE = os.path.join(PROJECT_DIR, 'data', 'conveyor_sst.csv')


def get_row(p: int, lon: int, lat: int, years: list[str]) -> pl.DataFrame:
    data = API.time_series(
        table=TABLE.Table_Name,
        variable=TABLE.Variable,
        dt1=f'{years[0]}-01-01',
        dt2=f'{years[-1]}-12-31',
        lat1=lat+0.125,  # Points are every ¼°, but start at -89,875
        lat2=lat+0.125,
        lon1=lon+0.125,  # Points are every ¼°, but start at -179.875
        lon2=lon+0.125,
        depth1=0,
        depth2=0,
    )
    data = (
        pl.from_pandas(data)
        .with_columns(
            pl.col('time').str.strptime(
                pl.Datetime).cast(pl.Datetime).dt.year()
        )
        .groupby(['time', 'lat', 'lon'])
        .agg(pl.col('sst').mean())
        .sort('time')
        .pivot(
            index=['lon', 'lat'],
            columns='time',
            values='sst',
        )
        .with_columns(pl.lit(p).alias('path'))
        .select([
            pl.col('path'),
            (pl.col('lon')-0.125).cast(pl.Int32).alias('longitude'),
            (pl.col('lat')-0.125).cast(pl.Int32).alias('latitude'),
        ] + years
        )
    )
    return data


def get_temp_data(path):

    years = [str(y) for y in range(1982, 2022)]
    columns = ['path', 'longitude', 'latitude'] + years
    schema = {
        'path': pl.Int32(),
        'longitude': pl.Int32(),
        'latitude': pl.Int32(),
    }
    for y in years:
        schema[y] = pl.Float64()
    temp_data = pl.DataFrame(schema=schema)

    for _, p, lon, lat in path.iter_rows():

        data = get_row(p, lon, lat, years)
        # data = API.time_series(
        #     table=TABLE.Table_Name,
        #     variable=TABLE.Variable,
        #     dt1='1982-01-01',
        #     dt2='2021-12-31',
        #     lat1=lat+0.125,  # Points are every ¼°, but start at -89,875
        #     lat2=lat+0.125,
        #     lon1=lon+0.125,  # Points are every ¼°, but start at -179.875
        #     lon2=lon+0.125,
        #     depth1=0,
        #     depth2=0,
        # )
        # data = (
        #     pl.from_pandas(data)
        #     .with_columns(
        #         pl.col('time').str.strptime(
        #             pl.Datetime).cast(pl.Datetime).dt.year()
        #     )
        #     .groupby(['time', 'lat', 'lon'])
        #     .agg(pl.col('sst').mean())
        #     .sort('time')
        #     .pivot(
        #         index=['lon', 'lat'],
        #         columns='time',
        #         values='sst',
        #     )
        #     .with_columns(pl.lit(p).alias('path'))
        #     .select([
        #         pl.col('path'),
        #         (pl.col('lon')-0.125).cast(pl.Int32).alias('longitude'),
        #         (pl.col('lat')-0.125).cast(pl.Int32).alias('latitude'),
        #     ] + years)
        # )

        temp_data = temp_data.join(data, on=columns, how='outer')

    temp_data.write_csv(OUTFILE)


def main():
    os.chdir(PROJECT_DIR)

    # Get temperature means for each point if not already.
    conveyor_path = pl.read_csv(CONVEYOR_PATH_FILE)

    if not os.path.exists(OUTFILE):
        get_temp_data(conveyor_path)


if __name__ == '__main__':
    main()
