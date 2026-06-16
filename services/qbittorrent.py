#!/usr/bin/env python3
"""Minimal client for the qBittorrent WebUI API (v2).

Used to inject freshly created torrents straight into a running
qBittorrent instance, pointed at the transcode output so the client can
recheck and seed immediately.
"""

import os
import logging

import requests

from models.exceptions import QBittorrentException

LOGGER = logging.getLogger("qbittorrent")


class QBittorrentClient:
    def __init__(self, host: str, username: str = "", password: str = ""):
        # qBittorrent rejects requests whose Referer/Origin don't match the
        # host (CSRF protection), so normalise the base URL and send it along.
        self.base_url = host.rstrip("/")
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.headers.update({"Referer": self.base_url})

        # When no credentials are configured we assume the WebUI bypasses
        # authentication (e.g. "Bypass authentication for clients on localhost")
        # and skip the login round-trip entirely.
        if username or password:
            self._login()
        else:
            LOGGER.info("No qBittorrent credentials set; assuming auth is bypassed.")

    def _login(self):
        r = self.session.post(
            f"{self.base_url}/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
        )
        if r.status_code == 403:
            raise QBittorrentException(
                "qBittorrent refused login (403); check that the host is allowed "
                "to bypass CSRF and that the WebUI is reachable at this address"
            )
        r.raise_for_status()
        if r.text.strip() != "Ok.":
            raise QBittorrentException("qBittorrent login failed: bad username or password")
        LOGGER.info("qBittorrent session opened successfully.")

    def add_torrent(
        self,
        torrent_path: str,
        savepath: str | None = None,
        category: str | None = None,
        tags: str | None = None,
        paused: bool = False,
        auto_tmm: bool = False,
    ):
        """Add a .torrent file to qBittorrent.

        savepath should point at the directory that *contains* the torrent's
        top-level folder, so qBittorrent finds the existing files and seeds.
        """
        with open(torrent_path, "rb") as f:
            files = {
                "torrents": (
                    os.path.basename(torrent_path),
                    f.read(),
                    "application/x-bittorrent",
                )
            }

        data: dict[str, str] = {
            "autoTMM": "true" if auto_tmm else "false",
            "paused": "true" if paused else "false",
            # qBittorrent 5.x renamed paused -> stopped; send both for compat.
            "stopped": "true" if paused else "false",
        }
        if savepath:
            data["savepath"] = savepath
        if category:
            data["category"] = category
        if tags:
            data["tags"] = tags

        r = self.session.post(
            f"{self.base_url}/api/v2/torrents/add", data=data, files=files
        )
        r.raise_for_status()
        if r.text.strip() != "Ok.":
            raise QBittorrentException(
                f"qBittorrent rejected the torrent: {r.text.strip() or r.status_code}"
            )
