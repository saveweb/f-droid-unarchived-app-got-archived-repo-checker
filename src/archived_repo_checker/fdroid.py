import json
import os
import sys
import yaml
import threading
from queue import Queue

import httpx

from archived_repo_checker import is_archived_repo


def get_repo_ok_pkgs() -> dict[str, dict]:
    assert os.path.exists("index-v2.json"), "index-v2.json not found"
    with open("index-v2.json", "r") as f:
        pkgs = json.load(f)["packages"]

    repo_ok_pkgs = {}

    print("Checking packages...")
    for idx, pkg_name in enumerate(pkgs):
        print(f'{idx}/{len(pkgs)}', pkg_name, end="\r")
        pkg = pkgs[pkg_name]
        metadata: dict = pkg["metadata"]
        versions = pkg["versions"]
        if get_fdroid_data_defined_repo(pkg_name) and not is_NoSourceSince(versions):
            repo_ok_pkgs[pkg_name] = metadata
    print(" " * 40, end="\r")

    return repo_ok_pkgs


def is_NoSourceSince(versions: dict) -> bool:
    """The source code is no longer available, no updates possible"""
    versions_list = list(versions.values())
    # sort by added, highest version first
    versions_list.sort(key=lambda x: x["added"], reverse=True)
    if versions and "antiFeatures" in versions_list[0]:
        return "NoSourceSince" in versions_list[0]["antiFeatures"]

    return False


# def get_sourceCode(metadata: dict) -> str:
#     sourceCode = metadata.get("sourceCode", "")
#     if not sourceCode:
#         return ""

#     assert (
#         "http://" in sourceCode or "https://" in sourceCode
#     ), f"Invalid URL: {sourceCode}"
#     return sourceCode


global_client = httpx.Client(
    http2=True,
    headers={
        "User-Agent": "archived_repo_checker/0.1.0 (archived_repo_checker checker)",
        "language": "en-US,en;q=0.5",
    },
    timeout=10,
)
def get_fdroid_data_defined_repo(pkg_name: str) -> str|None:
    # https://gitlab.com/fdroid/fdroiddata/-/raw/master/metadata/{pkg_name}.yml
    if os.path.exists(f"/tmp/fdroiddata/metadata/{pkg_name}.yml"):
        with open(f"/tmp/fdroiddata/metadata/{pkg_name}.yml", "r") as f:
            yml = yaml.safe_load(f)
            Repo = yml.get("Repo", None)
            return Repo

    url = f"https://gitlab.com/fdroid/fdroiddata/-/raw/master/metadata/{pkg_name}.yml"
    try:
        r = global_client.get(url)
        if r.status_code != 200:
            return None
        yml = yaml.safe_load(r.text)
        Repo = yml.get("Repo", None)
        return Repo
    except Exception as e:
        print("ERR:", e, file=sys.stderr)
        return None


def main():
    checked: dict[str, dict] = {}

    if os.path.exists("checked.result.json"):
        with open("checked.result.json", "r") as f:
            checked = json.load(f)

    repo_ok_pkgs = get_repo_ok_pkgs()

    item_queue = Queue()
    for idx, item in enumerate(repo_ok_pkgs.items()):
        item_queue.put((idx, item))

    lock = threading.Lock()

    stop = False

    def worker():
        client = httpx.Client(
            http2=True,
            headers={
                "User-Agent": "is_archived_repo/0.1.0 (is_archived_repo checker)",
                "language": "en-US,en;q=0.5",
            },
            timeout=10,
        )
        while not item_queue.empty() and not stop:
            idx, item = item_queue.get()
            pkg, metadata = item
            repo = get_fdroid_data_defined_repo(pkg_name=pkg)
            assert repo, f"Repo not found: {pkg}"
            print(f"{idx}/{len(repo_ok_pkgs)}", pkg, repo, end="          \r")
            lock.acquire()
            if pkg in checked and checked[pkg]["comfirmed"]:
                lock.release()
                item_queue.task_done()
                continue
            lock.release()
            try:
                res = is_archived_repo(repo, client=client)
                lock.acquire()
                checked[pkg] = {
                    "comfirmed": res.comfirmed,
                    "repo": repo,
                    "repo_real": res.repo_real,
                    "repo_deleted": res.repo_deleted,
                    "repo_archived": res.repo_archived,
                    "error": str(res.error) if res.error else None,
                }
                lock.release()
                if not res.comfirmed:
                    print(f"not comfirmed: https://f-droid.org/packages/{pkg} | {repo} <-> {res.error} |")
            finally:
                item_queue.task_done()

    threads : list[threading.Thread] = []
    for _ in range(5):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("Exiting...")
        stop = True
        for t in threads:
            t.join()
        print("Exited")

    lock.acquire()
    with open("checked.result.json", "w") as f:
        json.dump(checked, f, indent=2)
    lock.release()


if __name__ == "__main__":
    main()
