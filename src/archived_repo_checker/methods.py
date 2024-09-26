import httpx
import re
from typing import Optional
from archived_repo_checker.utils import Result

def github_check(url: str, response: httpx.Response) -> Result:
    if "github.com/" not in url:
        return Result()
    if (
        "his repository has been archived by the" in response.text
        and "It is now read-only." in response.text
    ):
        return Result(repo_archived=True)

    return Result(repo_archived=False)

GITHUB_REPO_URL = re.compile(r'https?://github\.com/[\w-]+/[\w-]+(?!(?:\.git)?/?[\w-])')
GITHUB_URL_BLACKLIST = re.compile(r'github\.com/(apps|enterprise|features|solutions)')
def moved_to_github_check(client: httpx.Client, url: str, response: httpx.Response, sample_commit_hash: str, res: Result):
    err = None
    for newurl in set(GITHUB_REPO_URL.findall(response.text)):
        if newurl != url and not GITHUB_URL_BLACKLIST.search(newurl):
            response = client.get(f'{newurl}/branch_commits/{sample_commit_hash}')
            if response.status_code == 200:
                if 'js-spoofed-commit-warning-trigger' not in response.text:
                    res.moved_to = newurl
                    return
            elif response.status_code != 404:
                err = Exception(f"HTTP status code: {response.status_code}")
    if err:
        res.error = err
        res.confirmed = False


def gitlab_check(url: str, response: httpx.Response) -> Result:
    if not (("gitlab.com/" in url) or ("_gitlab_session" in response.cookies)):
        return Result()
    if (
        "This is an archived project. Repository and other project resources are read-only."
        in response.text
    ):
        return Result(repo_archived=True)

    return Result(repo_archived=False)

GITLAB_REPO_URL = re.compile(r'https?://gitlab\.com/[\w-]+/[\w-]+(?!(?:\.git)?/?[\w-])')
GITLAB_URL_BLACKLIST = re.compile(r'gitlab\.com/(api|namespace\d+)')
def moved_to_gitlab_check(client: httpx.Client, url: str, response: httpx.Response, sample_commit_hash: str, res: Result):
    err = None
    for newurl in set(GITLAB_REPO_URL.findall(response.text)):
        if newurl != url and not GITLAB_URL_BLACKLIST.search(newurl):
            response = client.head(f'{newurl}/-/commit/{sample_commit_hash}')
            if response.status_code == 200:
                res.moved_to = newurl
                return
            elif response.status_code != 404:
                err = Exception(f"HTTP status code: {response.status_code}")
    if err:
        res.error = err
        res.confirmed = False


def gitea_check(url: str, response: httpx.Response) -> Result:
    if not (
        (
            "Powered by Gitea" in response.text
            and "https://about.gitea.com" in response.text
        )
        or ("codeberg.org/" in url)
    ):
        return Result()

    assert "English" in response.text, "Gitea instance is not in English"

    if (
        "This repository has been archived on" in response.text
        and "You can view files and clone it, but cannot push or open issues or pull requests."
        in response.text
    ):
        return Result(repo_archived=True)

    return Result(repo_archived=False)


def gitee_check(url: str, response: httpx.Response) -> Result:
    if "gitee.com/" not in url:
        return Result()

    # https://gitee.com/help/articles/4343
    if (
        "当前仓库属于关闭状态" in response.text
        or "当前仓库属于暂停状态" in response.text
    ):
        return Result(repo_archived=True)

    return Result(repo_archived=False)
