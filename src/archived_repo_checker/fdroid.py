import argparse
import glob
import json
import os
from typing import Optional
import yaml
import threading
from queue import Queue

import httpx

from archived_repo_checker import is_archived_repo


def get_repo_ok_pkgs(metadata_dir) -> dict[str, dict]:
    yamls = glob.glob(glob.escape(metadata_dir) + "/*.yml")

    repo_ok_pkgs = {}

    print("Loading packages...")
    for idx, yml_path in enumerate(yamls):
        print(f'\33[2K{idx+1}/{len(yamls)}', os.path.basename(yml_path), end="\r")
        with open(yml_path, "r") as f:
            yml = yaml.safe_load(f)
            if 'NoSourceSince' not in yml and yml.get('ArchivePolicy', 3) != 0:
                repo_ok_pkgs[yml_path] = yml

    print() # just get a newline

    return repo_ok_pkgs


# def get_sourceCode(metadata: dict) -> str:
#     sourceCode = metadata.get("sourceCode", "")
#     if not sourceCode:
#         return ""

#     assert (
#         "http://" in sourceCode or "https://" in sourceCode
#     ), f"Invalid URL: {sourceCode}"
#     return sourceCode


def main():
    parser = argparse.ArgumentParser(description="Check all F-Droid metadata files for archived repositories")
    parser.add_argument("metadata_dir", help="Directory with F-Droid metadata files")
    args = parser.parse_args()

    checked: dict[str, dict] = {}

    if os.path.exists("checked.result.json"):
        with open("checked.result.json", "r") as f:
            checked = json.load(f)

    repo_ok_pkgs = get_repo_ok_pkgs(args.metadata_dir)

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
            repo: Optional[str] = metadata.get('Repo', None)
            if repo is None\
                or not repo.startswith("http") \
                or "git.code.sf.net/p/" in repo:
                # Fallback to SourceCode
                repo = metadata.get("SourceCode", None)

            print(f"\33[2K{idx+1}/{len(repo_ok_pkgs)}", os.path.basename(pkg), repo, end="\r")
            lock.acquire()
            if pkg in checked and checked[pkg]["confirmed"]:
                lock.release()
                item_queue.task_done()
                continue
            lock.release()
            try:
                builds = metadata.get('Builds', [])
                cur_build = next((build for build in builds if build['versionCode'] == metadata['CurrentVersionCode']), {})
                if not cur_build and len(builds) > 0:
                    # just grab the last build
                    cur_build = builds[-1]
                res = is_archived_repo(repo, cur_build.get('commit', None), client=client)
                lock.acquire()
                checked[pkg] = {
                    "confirmed": res.confirmed,
                    "repo": repo,
                    "repo_real": res.repo_real,
                    "repo_deleted": res.repo_deleted,
                    "repo_archived": res.repo_archived,
                    "moved_to": res.moved_to,
                    "error": str(res.error) if res.error else None,
                }
                lock.release()
                if not res.confirmed:
                    print(f"not confirmed: {os.path.basename(pkg)} | {repo} <-> {res.error} |")
            finally:
                item_queue.task_done()

    print("Checking packages...")
    threads : list[threading.Thread] = []
    for _ in range(5):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
        print("") # Newline for status output
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
