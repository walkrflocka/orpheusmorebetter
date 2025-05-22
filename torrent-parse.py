#!/usr/bin/env python

import os
import json
import argparse
import sys
import logging

lockfile = os.path.expanduser('~/.orpheusmorebetter/parse.lock')


def main():
    if os.path.exists(lockfile):
        logging.error("Found lockfile, exiting....")

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog='orpheusmorebetter')
    parser.add_argument('--cache', help='the location of the cache',
                        default=os.path.expanduser('~/.orpheusmorebetter/cache-crawl'))

    args = parser.parse_args()
    while parse_stuff(args.cache) and not os.path.exists(lockfile):
        logging.info("Done encoding cycle")


def parse_stuff(cache_file):
    open(lockfile, 'w').close()
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
    except:
        cache = []
        with open(cache_file, 'w') as f:
            json.dump(cache, f)

    permalinks = []
    cache_new = []
    for torrent in cache:
        if torrent['done']:
            permalinks.append('"https://orpheus.network/{0}"'.format(torrent['permalink']))
        else:
            cache_new.append(torrent)

    if len(permalinks) == 0:
        return False

    cmdline = "python3 orpheusmorebetter.py {0}".format(' '.join(permalinks))
    with open(cache_file, 'w') as f:
        json.dump(cache_new, f)

    logging.info("Executing... {0}".format(cmdline))
    os.system(cmdline)
    os.remove(lockfile)
    return True


if __name__ == '__main__':
    main()
