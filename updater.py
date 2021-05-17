#!/usr/bin/env python

import os
import tarfile
import itertools
import sys
import shutil
import argparse
import requests

BASE_URL = "https://api.github.com"
GE_PROTON_REPO = "/repos/GloriousEggroll/proton-ge-custom/releases/latest"


class ProtonVersion:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.local = self.url != ""
        self.version, self.tags = self.split_version()

    def split_version(self):
        parts = self.name.lstrip("Proton-").split("-")
        version = list(map(int, parts[0].split(".")))
        tags = parts[1::]
        return version, tags

    def __lt__(self, other):
        return self.version < other.version


class Updater:
    def __init__(self, tmpdir, steam_compat_dir):
        self.steam_compat_dir = steam_compat_dir
        self.installed_versions = []
        self.available_version = None
        self.tmpdir = tmpdir
        self.get_latest()
        self.get_local_versions()

    def get_local_versions(self):
        installed_versions = os.listdir(self.steam_compat_dir)
        if installed_versions:
            installed_proton_versions = filter(
                lambda x: x.startswith("Proton"), installed_versions
            )
            self.installed_versions = list(
                map(lambda x: ProtonVersion(x, ""), installed_proton_versions)
            )

    def get_latest(self):
        r = requests.get(BASE_URL + GE_PROTON_REPO)
        latest = r.json()
        for asset in latest.get("assets"):
            name = asset.get("name")
            if "tar.gz" in name:
                url = asset.get("browser_download_url")

        if not url:
            raise Exception("Failed to find tarball url")

        self.available_version = ProtonVersion(name.strip(".tar.gz"), url)

    def check_update_available(self) -> bool:
        for v in self.installed_versions:
            if v.name == self.available_version.name:
                return False

        return True

    def fetch_update(self, version, tmpdir):
        path = f"{tmpdir}/{version.name}"

        r = requests.get(version.url, stream=True)
        spinner = itertools.cycle(["|", "/", "-", "\\"])
        with open(path, "wb") as fp:
            for chunk in r.iter_content(chunk_size=128):
                sys.stdout.write(f"\rDownloading, please wait. {next(spinner)}")
                sys.stdout.flush()
                fp.write(chunk)
        print("\n")
        return path

    def unpack_update(self, path):
        with tarfile.open(path) as tarball:
            tarball.extractall(path=self.steam_compat_dir)

    def cleanup_old_versions(self):
        for f in os.listdir(self.steam_compat_dir):
            if f == self.available_version:
                continue
            os.remove(os.path.join(self.steam_compat_dir, f))

    def do_update(self):
        print("Currently installed:")
        for v in self.installed_versions:
            print(f"\t{v.name}")

        if not self.check_update_available():
            print("No new versions available")
            return

        print(f"Available: {self.available_version.name}")
        yes_no = input("Perform update? [y/n]\t")
        if yes_no.lower() != "y":
            return

        tmp_file = self.fetch_update(self.available_version, self.tmpdir)

        try:
            print("Unpacking update")
            self.unpack_update(tmp_file)
        except tarfile.ExtractError as exc:
            print(f"Failed to unpack {tmp_file}, exception: {exc}")
            shutil.rmtree(
                os.path.join(self.steam_compat_dir, self.available_version.name)
            )
            os.remove(tmp_file)

        print(f"\nDone, updated proton version to {self.available_version.name}")


def main(args):
    if not os.path.isdir(args.steamdir):
        print(f"Steam compatibility tools not found at {args.steamdir}, creating it")
        os.mkdir(args.steamdir)

    updater = Updater(args.tmpdir, args.steamdir)
    updater.do_update()
    if args.cleanup:
        updater.cleanup_old_versions()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Updater for GloriousEggroll's custom Proton versions."
    )
    parser.add_argument(
        "--tmpdir",
        default="/tmp",
        required=False,
        help="Temporary directory for downloads, defaults to /tmp",
    )

    parser.add_argument(
        "--cleanup",
        default=False,
        required=False,
        action="store_true",
        help="Cleanup old proton versions",
    )

    parser.add_argument(
        "--steamdir",
        default=os.path.expanduser("~/.steam/steam/compatibilitytools.d"),
        required=False,
        help="Path to steam directory",
    )

    args = parser.parse_args()
    main(args)
