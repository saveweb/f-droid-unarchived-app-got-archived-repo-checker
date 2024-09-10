import httpx


def github_check(url: str, response: httpx.Response) -> tuple[bool, bool]:
    if "github.com/" not in url:
        return False, False
    if (
        "his repository has been archived by the" in response.text
        and "It is now read-only." in response.text
    ):
        return True, True

    return True, False


def gitlab_check(url: str, response: httpx.Response) -> tuple[bool, bool]:
    if not (("gitlab.com/" in url) or ("_gitlab_session" in response.cookies)):
        return False, False
    if (
        "This is an archived project. Repository and other project resources are read-only."
        in response.text
    ):
        return True, True

    return True, False


def gitea_check(url: str, response: httpx.Response) -> tuple[bool, bool]:
    if not (
        (
            "Powered by Gitea" in response.text
            and "https://about.gitea.com" in response.text
        )
        or ("codeberg.org/" in url)
    ):
        return False, False

    assert "English" in response.text, "Gitea instance is not in English"

    if (
        "This repository has been archived on" in response.text
        and "You can view files and clone it, but cannot push or open issues or pull requests."
        in response.text
    ):
        return True, True

    return True, False


def gitee_check(url: str, response: httpx.Response) -> tuple[bool, bool]:
    if "gitee.com/" not in url:
        return False, False

    # https://gitee.com/help/articles/4343
    if (
        "当前仓库属于关闭状态" in response.text
        or "当前仓库属于暂停状态" in response.text
    ):
        return True, True

    return True, False
