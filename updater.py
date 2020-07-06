import requests
import os
import tarfile
import itertools
import sys
import shutil
import argparse

BASE_URL = "https://api.github.com"
GE_PROTON_REPO = "/repos/GloriousEggroll/proton-ge-custom/releases/latest"
STEAM_COMPAT_PATH = os.path.expanduser("~/.steam/steam/compatibilitytools.d")


class ProtonVersion:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.local = self.url != ""
        self.version, self.tags = self.split_version()

    def split_version(self):
        parts = self.name.lstrip("Proton-").split("-")
        version = list(
            map(lambda x: int(x), parts[0].split(".")))
        tags = parts[1::]
        return version, tags

    def __lt__(self, other):
        return self.version < other.version


def get_local_versions():
    installed_versions = os.listdir(STEAM_COMPAT_PATH)
    return list(map(lambda x: ProtonVersion(x, ""), installed_versions))


def get_latest() -> ProtonVersion:
    r = requests.get(BASE_URL + GE_PROTON_REPO)
    latest = r.json()
    return ProtonVersion(latest["name"], latest.get("assets")[0].get("browser_download_url"))


def check_update_available(installed_versions, latest_version) -> bool:
    for v in installed_versions:
        if v.name == latest_version.name:
            return False

    return True


def fetch_update(version, tmpdir):
    path = f"{tmpdir}/{version.name}"
    if os.path.isfile(path):
        print("File already downloaded.")
        return path

    r = requests.get(version.url, stream=True)
    spinner = itertools.cycle(["|", "/", "-", "\\"])
    with open(path, "wb") as fp:
        for chunk in r.iter_content(chunk_size=128):
            sys.stdout.write(f"\rDownloading, please wait. {next(spinner)}")
            sys.stdout.flush()
            fp.write(chunk)

    return path


def unpack_update(path):
    print("Unpacking update")
    with tarfile.open(path) as tarball:
        tarball.extractall(path=STEAM_COMPAT_PATH)


def cleanup_old_versions():
    for f in os.listdir(STEAM_COMPAT_PATH):

        os.remove(os.path.join(STEAM_COMPAT_PATH, f))


def do_update(latest_version, tmpdir):

    tmp_file = fetch_update(latest_version, tmpdir)
    try:
        print("Unpacking update")
        unpack_update(tmp_file)
    except Exception as e:
        print(f"Failed to unpack {tmp_file}, exception: {e}")
        shutil.rmtree(os.path.join(STEAM_COMPAT_PATH, latest_version.name))
        os.remove(tmp_file)
        return

    print(
        f"\nDone, updated proton version to {latest_version.name}")


def main(args):
    if args.steamdir:
        pass

    local_versions = get_local_versions()
    latest_version = get_latest()

    if check_update_available(local_versions, latest_version):
        print("Installed:")
        for version in local_versions:
            print(f"\t{version.name}")
        print(f"Available: {latest_version.name}")
        do_update(latest_version, args.tmpdir)
        if args.cleanup:
            cleanup_old_versions()
        return

    print("No updates available")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Updater for GloriousEggroll's custom Proton versions.")
    parser.add_argument("--tmpdir",
                        default="/tmp",
                        required=False,
                        help="Temporary directory for downloads, defaults to /tmp")

    parser.add_argument("--cleanup",
                        default=False,
                        required=False,
                        action="store_true",
                        help="Cleanup old proton versions")

    parser.add_argument("--steamdir",
                        default="~/.steam",
                        required=False,
                        help="Path to steam directory")

    args = parser.parse_args()
    main(args)
