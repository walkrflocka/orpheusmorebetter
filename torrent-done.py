#!/usr/bin/env python3

from sys import argv, exit
import json


def main():
    torrent_hash = argv[5].upper()

    # find the hash and set done = true
    cache = json.load(open('~/.orpheusmorebetter/cache-crawl'))
    for torrent in cache:
        if torrent['hash'] == torrent_hash:
            torrent['done'] = True
            json.dump(cache, open('~/.orpheusmorebetter/cache-crawl', 'wb'))
            exit(0)

    exit(1)
