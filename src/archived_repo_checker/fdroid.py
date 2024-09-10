import json
import os
import threading
from queue import Queue

import httpx

from archived_repo_checker import is_archived_repo


def get_src_ok_pkgs() -> dict[str, dict]:
    assert os.path.exists("index-v2.json"), "index-v2.json not found"
    with open("index-v2.json", "r") as f:
        pkgs = json.load(f)["packages"]

    src_ok_pkgs = {}

    for pkg_name in pkgs:
        pkg = pkgs[pkg_name]
        metadata: dict = pkg["metadata"]
        versions = pkg["versions"]
        if get_sourceCode(metadata) and not is_NoSourceSince(versions):
            src_ok_pkgs[pkg_name] = metadata

    return src_ok_pkgs


def is_NoSourceSince(versions: dict) -> bool:
    """The source code is no longer available, no updates possible"""
    versions_list = list(versions.values())
    # sort by added, highest version first
    versions_list.sort(key=lambda x: x["added"], reverse=True)
    if versions and "antiFeatures" in versions_list[0]:
        return "NoSourceSince" in versions_list[0]["antiFeatures"]

    return False


def get_sourceCode(metadata: dict) -> str:
    sourceCode = metadata.get("sourceCode", "")
    if not sourceCode:
        return ""

    assert (
        "http://" in sourceCode or "https://" in sourceCode
    ), f"Invalid URL: {sourceCode}"
    return sourceCode


def main():
    checked: dict[str, dict] = {}

    if os.path.exists("checked.result.json"):
        with open("checked.result.json", "r") as f:
            checked = json.load(f)

    src_ok_pkgs = get_src_ok_pkgs()

    item_queue = Queue()
    for idx, item in enumerate(src_ok_pkgs.items()):
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
            src = get_sourceCode(metadata)
            print(f"{idx}/{len(src_ok_pkgs)}", pkg, src, end="          \r")
            lock.acquire()
            if pkg in checked and checked[pkg]["comfirmed"]:
                lock.release()
                item_queue.task_done()
                continue
            lock.release()
            try:
                res = is_archived_repo(src, client=client)
                lock.acquire()
                checked[pkg] = {
                    "comfirmed": res.comfirmed,
                    "src": src, # f-droid metadata::sourceCode
                    "src_real": res.src_real,
                    "repo_deleted": res.repo_deleted,
                    "repo_archived": res.repo_archived,
                    "error": str(res.error) if res.error else None,
                }
                lock.release()
                if not res.comfirmed:
                    print(f"not comfirmed: https://f-droid.org/packages/{pkg} | {src} <-> {res.error} |")
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
