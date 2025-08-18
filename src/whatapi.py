#!/usr/bin/env python3
import re
import time
import requests
import logging
import re
from bs4 import BeautifulSoup, Tag

from typing import Optional, List, Dict, Any, Set, Union, Literal

from models.formats import perfect_three

# gazelle is picky about case in searches with &media=x
media_search_map = {
    "cd": "CD",
    "dvd": "DVD",
    "vinyl": "Vinyl",
    "soundboard": "Soundboard",
    "sacd": "SACD",
    "dat": "DAT",
    "web": "WEB",
    "blu-ray": "Blu-ray",
}

lossless_media = set(media_search_map.keys())

LOGGER = logging.getLogger("api")


def allowed_transcodes(torrent: str) -> List[str]:
    """Some torrent types have transcoding restrictions."""
    preemphasis = re.search(
        r"pre[- ]?emphasi(s(ed)?|zed)", torrent["remasterTitle"], flags=re.IGNORECASE
    )
    if preemphasis:
        return []
    else:
        return list(perfect_three.keys())


class LoginException(Exception):
    pass


class RequestException(Exception):
    pass


class WhatAPI:
    def __init__(
        self,
        username: str,
        password: str,
        endpoint: str = "https://orpheus.network/",
        totp: Optional[str] = None,
    ):
        self.browser = None
        self.username: str = username
        self.password: str = password
        self.totp: Optional[str] = totp

        assert endpoint.endswith("/")
        self.base_url: str = endpoint

        self.last_request = time.time()
        self.min_sec_between_requests = 5.0

        self.session = requests.Session()
        self._login()
        self.authkey = ""

        ind_data = self.request_ajax("index", method="GET")
        try:
            self.user_id = ind_data["id"]
            self.authkey: str = ind_data["authkey"]
            self.passkey: str = ind_data["passkey"]
        except KeyError as e:
            raise ValueError(
                "Orpheus index did not return one or more expected fields"
            ) from e

    def _login(self):
        """Prime the session with a login cookie so we can do more tomfoolery later"""
        r = self.session.post(
            url=self.base_url + "login.php",
            data={  # it has to be set in the BODY not params, moron
                "username": self.username,
                "password": self.password,
                "mfa": self.totp,
                "login": "Log in"
            },
        )

        # Handle 403 errors specifically - probably IP banned
        # Could be due to too many failed login attempts?
        if r.status_code == 403:
            # Try to extract additional details from the response
            match = re.search(r"Additional details:?\s*([^<\n]+)", r.text)
            if match:
                error_message = match.group(1).strip()
                LOGGER.error(f"Login failed with 403 error: {error_message}")
                raise LoginException(f"403 Forbidden: {error_message}")
            else:
                LOGGER.error("Login failed with 403 error: no additional details available")
                raise LoginException("403 Forbidden")

        # For other HTTP errors
        r.raise_for_status()

        # If 200 OK, check for login warnings before continuing. e.g. old 2FA code
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, features="lxml")
            warning_div = soup.find("div", class_="warning-login")
            if warning_div:
                # Extract & show warning message
                warning_text = warning_div.get_text(separator=" ", strip=True)
                warning_text = re.sub(r'\s+', ' ', warning_text)
                warning_text = warning_text.replace(".", ".\n")
                LOGGER.error(f"Login failed with warning: \n{warning_text}")
                raise LoginException(f"Login failed: {warning_text}")

        assert r.cookies is not None
        LOGGER.info("Orpheus session opened successfully.")

    def request_ajax(
        self,
        action: str,
        data: Optional[Dict[str, Union[str, int]]] = None,
        method: Literal["POST", "GET"] = "POST",
        files: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Makes an AJAX request at a given action page"""
        time_since_last_req = time.time() - self.last_request
        if time_since_last_req < self.min_sec_between_requests:
            time.sleep(self.min_sec_between_requests - time_since_last_req)

        ajaxpage = "{0}ajax.php".format(self.base_url)
        params = {
            "action": action,
        }

        params.update(kwargs)

        if method == "GET":
            params.update({"auth": self.authkey})
            r = self.session.get(ajaxpage, params=params)
        elif method == "POST":
            if data is not None:
                data.update({"auth": self.authkey})
            r = self.session.post(ajaxpage, params=params, data=data, files=files)

        self.last_request = time.time()

        try:
            LOGGER.debug(f"Received response with status code {r.status_code}")
            parsed = r.json()
            if parsed["status"] != "success":
                raise RequestException(parsed["error"])
            return parsed["response"]
        except ValueError as e:
            raise RequestException from e

    def request_webpage(self, action: str, **kwargs: Any):
        """Grab the HTML content of a page"""
        time_since_last_req = time.time() - self.last_request
        if time_since_last_req < self.min_sec_between_requests:
            time.sleep(self.min_sec_between_requests - time_since_last_req)

        url = self.base_url + action
        params = {"auth": self.authkey} | kwargs
        r = self.session.get(url, params=params, allow_redirects=False)
        self.last_request = time.time()
        return r.content

    def get_artist(
        self, id: Optional[int] = None, format: str = "MP3", best_seeded: bool = True
    ):
        res = self.request_ajax("artist", method="GET", id=id)
        torrentgroups = res["torrentgroup"]
        keep_releases: List[str] = []
        for release in torrentgroups:
            torrents = release["torrent"]
            best_torrent = torrents[0]
            keeptorrents = []
            for t in torrents:
                if t["format"] != format:
                    keeptorrents.append(t)
                    continue

                if best_seeded:
                    if t["seeders"] > best_torrent["seeders"]:
                        keeptorrents = [t]
                        best_torrent = t
            release["torrent"] = list(keeptorrents)
            if len(release["torrent"]):
                keep_releases.append(release)
        res["torrentgroup"] = keep_releases
        return res

    def get_html(self, url: str):
        time_since_last_req = time.time() - self.last_request
        if time_since_last_req < self.min_sec_between_requests:
            time.sleep(self.min_sec_between_requests - time_since_last_req)

        params = {"auth": self.authkey}
        r = self.session.get(url, params=params, allow_redirects=False)
        self.last_request = time.time()
        return r.text

    def crawl_torrents_php(
        self,
        type: Literal["snatched", "uploaded"],
        media_params: List[str],
        skip: Optional[List[str]],
    ):
        LOGGER.info(f"Finding {type} torrents")
        url = f"{self.base_url}/torrents.php?type={type}&userid={self.user_id}&format=FLAC"

        for mp in media_params:
            page = 1
            done = False
            while not done:
                content = self.get_html(url + mp + f"&page={page}")

                soup = BeautifulSoup(content, features="lxml")
                torrent_tab = soup.find("table", class_="torrent_table")
                if not isinstance(torrent_tab, Tag):
                    LOGGER.info(f"Found no results for media {mp.replace('&media=', '')}")
                    break
                torrent_rows = torrent_tab.find_all("tr", class_="torrent_row")

                for row in torrent_rows:
                    group_info = row.find("div", class_="group_info")
                    torrent_info_pat = re.compile(
                        r"torrents\.php\?id=(\d+)&torrentid=(\d+)(?:#.*)?"
                    )

                    for a_tag in group_info.find_all("a"):
                        href = a_tag.get("href")
                        if href is None:
                            continue

                        match = torrent_info_pat.search(href)
                        if match is None:
                            continue

                        LOGGER.debug(f"Found torrent info {href}")

                        group_id: str = match.group(1)
                        torrent_id: str = match.group(2)

                        if skip is not None and torrent_id in skip:
                            continue

                        yield int(group_id), int(torrent_id)

                done = "page={0}".format(page + 1) not in content
                page += 1

    def get_candidates(
        self,
        mode: str,
        skip: Optional[List[str]] = None,
        media: Set[str] = lossless_media,
    ):
        if not media.issubset(lossless_media):
            raise ValueError(
                "Unsupported media type {0}".format((media - lossless_media).pop())
            )

        if not mode in ("snatched", "uploaded", "both", "all", "seeding"):
            raise ValueError("Unsupported candidate mode {0}".format(mode))

        # gazelle doesn't currently support multiple values per query
        # parameter, so we have to search a media type at a time;
        # unless it's all types, in which case we simply don't specify
        # a 'media' parameter (defaults to all types).

        if media == lossless_media:
            media_params = [""]
        else:
            media_params = ["&media={0}".format(media_search_map[m]) for m in media]

        pattern = re.compile(
            r'reportsv2\.php\?action=report&amp;id=(\d+)".*?torrents\.php\?id=(\d+).*?"',
            re.MULTILINE | re.IGNORECASE | re.DOTALL,
        )
        if mode == "snatched" or mode == "both" or mode == "all":
            yield from self.crawl_torrents_php("snatched", media_params, skip)

        if mode == "uploaded" or mode == "both" or mode == "all":
            yield from self.crawl_torrents_php("uploaded", media_params, skip)

        if mode == "seeding" or mode == "all":
            LOGGER.info("Using better.php to find Seeding")
            url = "{0}/better.php?method=transcode&filter=seeding".format(self.base_url)
            pattern = re.compile(r"torrents.php\?groupId=(\d+)&torrentid=(\d+)#\d+")
            content = self.get_html(url)
            for group_id, torrent_id in pattern.findall(content):
                if skip is None or torrent_id not in skip:
                    yield int(group_id), int(torrent_id)

    def upload(
        self,
        group: Dict[str, Dict[str, str]],
        torrent: Dict[str, str],
        new_torrent: str,
        format: str,
        description: Optional[str] = None,
    ):
        files = {
            "file_input": (
                "1.torrent",
                open(new_torrent, "rb"),
                "application/x-bittorrent",
            )
        }

        form: Dict[str, Union[str, int]] = {
            "type": "0",
            "groupid": group["group"]["id"],
        }

        if torrent["remastered"]:
            form.update(
                {
                    "remaster": True,
                    "remaster_year": str(torrent["remasterYear"]),
                    "remaster_title": torrent["remasterTitle"],
                    "remaster_record_label": torrent["remasterRecordLabel"],
                    "remaster_catalogue_number": torrent["remasterCatalogueNumber"],
                }
            )
        else:
            form.update(
                {
                    "remaster_year": "",
                    "remaster_title": "",
                    "remaster_record_label": "",
                    "remaster_catalogue_number": "",
                }
            )

        form.update(
            {
                "format": perfect_three[format]["format"],
                "bitrate": perfect_three[format]["encoding"],
                "media": torrent["media"],
            }
        )

        if description:
            release_desc = "\n".join(description)
            form["release_desc"] = release_desc

        self.request_ajax("upload", data=form, files=files, method="POST")

    def set_24bit(self, torrent: Dict[str, str]):
        data: Dict[str, Union[str, bool, None, int]] = {
            "submit": True,
            "type": 1,
            "action": "takeedit",
            "torrentid": torrent["id"],
            "media": torrent["media"],
            "format": torrent["format"],
            "bitrate": "24bit Lossless",
            "release_desc": torrent["description"],
        }
        if torrent["remastered"]:
            data["remaster"] = "on"
            data["remaster_year"] = torrent["remasterYear"]
            data["remaster_title"] = torrent["remasterTitle"]
            data["remaster_record_label"] = torrent["remasterRecordLabel"]
            data["remaster_catalogue_number"] = torrent["remasterCatalogueNumber"]

        url = "{0}/torrents.php?action=edit&id={1}".format(self.base_url, torrent["id"])

        while time.time() - self.last_request < self.min_sec_between_requests:
            time.sleep(0.1)
        self.session.post(url, data=data)
        self.last_request = time.time()

    def release_url(self, group: Dict[str, Dict[str, str]], torrent: Dict[str, str]):
        return "{0}/torrents.php?id={1}&torrentid={2}#torrent{3}".format(
            self.base_url, group["group"]["id"], torrent["id"], torrent["id"]
        )

    def permalink(self, torrent: Dict[str, str]):
        return "{0}/torrents.php?torrentid={1}".format(self.base_url, torrent["id"])

    def get_better(self, type: int = 3):
        p = re.compile(
            r'(torrents\.php\?action=download&(?:amp;)?id=(\d+)[^"]*).*(torrents\.php\?id=\d+(?:&amp;|&)torrentid=\2\#torrent\d+)',
            re.DOTALL,
        )
        out: List[Dict[str, str]] = []
        data = self.get_html("better.php?action=transcode&type=type")

        torrent: str
        perma: str
        id: str
        for torrent, id, perma in p.findall(data):
            out.append(
                {
                    "permalink": perma.replace("&amp;", "&"),
                    "id": int(id),
                    "torrent": torrent.replace("&amp;", "&"),
                }
            )
        return out

    def get_torrent(self, torrent_id: str):
        """Downloads the torrent at torrent_id using the authkey and passkey"""
        while time.time() - self.last_request < self.min_sec_between_requests:
            time.sleep(0.1)

        torrentpage = "{0}/torrents.php".format(self.base_url)
        params = {
            "action": "download",
            "id": torrent_id,
            "authkey": self.authkey,
            "torrent_pass": self.passkey,
        }

        r = self.session.get(torrentpage, params=params, allow_redirects=False)

        self.last_request = time.time() + 2.0
        if (
            r.status_code == 200
            and "application/x-bittorrent" in r.headers["content-type"]
        ):
            return r.content
        return None

    def get_torrent_info(self, id):
        return self.request_ajax("torrent", id=id, method="GET")["torrent"]
