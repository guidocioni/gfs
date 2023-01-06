import pandas as pd
import requests
import argparse
from tqdm.contrib.concurrent import process_map
import time
import random

"""
Script to download files from the NOMADS server.
Note that the number of workers and sleep commands are optimized
to nothit the throttling limit of the server. Unfortunately you 
cannot make the download process faster because you're going to 
hit this limit eventually.
"""

parser = argparse.ArgumentParser()

fcst_hours = [f"f{r:03d}" for r in range(3, 384, 3)]

parser.add_argument('-f', '--fcst', help='Forecast hour',
                    default=fcst_hours,
                    choices=fcst_hours,
                    nargs='+')
parser.add_argument('-v', '--vars', help='Variables',
                    default=['TMP'],
                    # choices=variables,
                    nargs='+')
parser.add_argument('-l', '--levs', help='Vertical levels',
                    default=['2 m above ground'],
                    # choices=variables,
                    nargs='+')
parser.add_argument('-d', '--date', help='Date (e.g. 20220826)', required=True)
parser.add_argument('-r', '--run', help='Run (e.g. 06)', required=True)
parser.add_argument('-o', '--folder', help='Output folder', default="./")

# Get the arguments passed from the command line
args = parser.parse_args()


def main():
    if len(args.vars) != len(args.levs):
        raise ValueError('Variables and levels should have the same size')
    # Create iterator for download
    it = [{'fcst': i} for i in args.fcst]
    # Launch downloading
    files = process_map(download, it, chunksize=10, max_workers=4)

    return files


def download(it):
    # Randomly sleep for some amount of time to not overload the server
    time.sleep(random.uniform(0.1, 1.1))
    # Unpack payload
    fcst = it['fcst']
    # Build url
    url = (
        "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/"
        f"gfs.{args.date}/{args.run}"
        "/atmos/"
        f"gfs.t{args.run}z.pgrb2.0p25.{fcst}"
    )
    idx_url = url + ".idx"
    # This contains the columns needed to get only the variables that we need
    sel = pd.DataFrame({'var': args.vars, 'level': args.levs})
    # Get the inventory file
    inventory = pd.read_csv(idx_url, sep=":", index_col=0,
                            names=['byte_begin', 'date', 'var', 'level', 'fcst', 'member'])
    inventory['byte_end'] = inventory.byte_begin.shift(
        -1).fillna(0).astype(int)
    # And only select the variables that we need
    selection = inventory.merge(sel, left_on=['var', 'level'], right_on=[
                                'var', 'level'], how='right')
    # Only select istantaneous and accumulated values (cause preciptation also has average)
    selection = selection[selection.fcst.str.contains(r'^\d+ hour fcst|^0-\d+ (?:hour|day) acc fcst')]
    # Rain accumulated is sometimes duplicated...don't know why, needs to be investigated
    selection = selection.drop_duplicates(subset=['var','level','fcst'])
    # Get the corresponding bytes sections in the file
    byte_selection = "bytes="
    byte_selection += ",".join(selection["byte_begin"].astype(
        str) + '-' + selection["byte_end"].astype(str))
    # Create the request
    headers = {"Range": byte_selection}
    # Wait again before launching the next request
    time.sleep(0.5)
    r = requests.get(url, headers=headers)
    # Check if we get some data, as the NOMADS servers are shit
    max_retry = 5
    retry = 0
    while (len(r.content) == 0) and (retry <= max_retry):
        # backoff just a little bit to make the server happy
        time.sleep(1)
        r = requests.get(url, headers=headers)
        retry += 1
    if retry == max_retry:
        print(f'WARNING: reached maximum limit of retries ({max_retry})')
    if r.status_code == 403:
        print(f'Could not download {url}')
        return None
    # Save the file
    filename = f"{args.folder}/grib_gfs_{args.date}_{args.run}_{fcst}"
    open(filename, "wb").write(r.content)

    return filename


if __name__ == "__main__":
    main()
