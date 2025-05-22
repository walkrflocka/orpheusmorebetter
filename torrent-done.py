#!/usr/bin/env python3

from sys import argv, exit
import json


def main():
    torrent_hash = argv[5].upper()

    # find the hash and set done = true
    with open('~/.orpheusmorebetter/cache-crawl', 'r') as f:
        cache = json.load(f)

    for torrent in cache:
        if torrent['hash'] == torrent_hash:
            torrent['done'] = True
            with open('~/.orpheusmorebetter/cache-crawl', 'w') as f:
                json.dump(cache, f)
            exit(0)

    exit(1)
