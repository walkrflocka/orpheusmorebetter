#!/usr/bin/env python3

import sys
import os
from configparser import ConfigParser
import json
import argparse
import logging

from .whatapi import WhatAPI
from models import Torrent


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog="orpheusmorebetter"
    )
    parser.add_argument(
        "-s",
        "--snatches",
        type=int,
        help="minimum amount of snatches required before transcoding",
        default=5,
    )
    parser.add_argument(
        "-b", "--better", type=int, help="better transcode search type", default=3
    )
    parser.add_argument("-c", "--count", type=int, help="backlog max size", default=5)
    parser.add_argument(
        "--config",
        help="the location of the configuration file",
        default=os.path.expanduser("~/.orpheusmorebetter/config"),
    )
    parser.add_argument(
        "--cache",
        help="the location of the cache",
        default=os.path.expanduser("~/.orpheusmorebetter/cache-crawl"),
    )

    args = parser.parse_args()

    config = ConfigParser()
    try:
        open(args.config)
        config.read(args.config)
    except:
        logging.error("Please run orpheusmorebetter once")
        sys.exit(2)

    username = config.get("whatcd", "username")
    password = config.get("whatcd", "password")
    torrent_dir = os.path.expanduser(config.get("whatcd", "torrent_dir"))

    api = WhatAPI(username, password)

    try:
        cache = json.load(open(args.cache))
    except:
        cache = []
        with open(args.cache, "w") as f:
            json.dump(cache, f)

    while len(cache) < args.count:
        logging.info(
            "Refreshing better.php and finding {0} candidates".format(
                args.count - len(cache)
            )
        )
        for item in api.get_better(args.better):
            if len(cache) >= args.count:
                break

            logging.info("Testing #{0}".format(item["id"]))
            info: Torrent = api.get_torrent_info(item["id"])
            if info.snatched < args.snatches:
                continue

            logging.info(
                "Fetching #{0} with {1} snatches".format(
                    info.id, info.snatched
                )
            )

            with open(
                os.path.join(torrent_dir, "%i.torrent" % item["id"]), "wb"
            ) as f:
                torrent_file = api.get_torrent_file(info.id)
                if isinstance(torrent_file, bytes):
                    f.write(torrent_file)
                else:
                    raise TypeError(f'Got unexpected response type for torrent file: {type(torrent_file)}')

            item["hash"] = info["infoHash"].upper()
            item["done"] = False

            with open(args.cache, 'rw') as f:
                cache = json.load(f)
                cache.append(item)
                json.dump(cache, f)

    logging.info("Nothing left to do")


if __name__ == "__main__":
    main()
