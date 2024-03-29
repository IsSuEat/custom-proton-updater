#!/usr/bin/env python

import os
import tarfile
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


class Updater:
    def __init__(self, tmpdir, steam_compat_dir):
        self.steam_compat_dir = steam_compat_dir
        self.installed_versions = []
        self.available_version = None
        self.tmpdir = tmpdir
        self.get_latest()
        self.get_local_versions()

    def get_local_versions(self):
        installed_compat_tools = os.listdir(self.steam_compat_dir)
        if installed_compat_tools:
            installed_proton_versions = filter(
                lambda x: "proton" in x.lower(), installed_compat_tools
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
        file_size = int(r.headers.get("Content-length", -1))

        if file_size == -1:
            raise Exception("Could not get conent size")

        print(f"Downloading {file_size / (1024*1024):.2f} mb")
        total_downloaded = 0
        with open(path, "wb") as fp:
            for chunk in r.iter_content(chunk_size=4096):
                total_downloaded += len(chunk)

                fp.write(chunk)
                done = int(50 * total_downloaded / file_size)
                sys.stdout.write(f"\r[{'=' * done}{' ' * (50 - done)}]")
                sys.stdout.flush()

        print("\n")
        return path

    def unpack_update(self, path):
        with tarfile.open(path) as tarball:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tarball, path=self.steam_compat_dir)

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

        print(f"Available: {self.available_version.name}\n")
        yes_no = input("Perform update? [Y/n]: ")
        if yes_no.lower() not in ["y", ""]:
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
    try:
        main(args)
    except KeyboardInterrupt:
        print("Aborted")
