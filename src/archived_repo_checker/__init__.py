import pprint
from typing import Optional

import logging
import httpx

from archived_repo_checker.handlers import not_found_handler
from archived_repo_checker.utils import Result, global_client
import archived_repo_checker.methods as methods

logger = logging.getLogger(__name__)


def _is_cloudflare_captcha(response: httpx.Response) -> bool:
    return response.headers.get("cf-mitigated", "") == "challenge"


def check_all(response: httpx.Response) -> tuple[bool, bool]:
    funcs = [
        methods.github_check,
        methods.gitlab_check,
        methods.gitea_check,
        methods.gitee_check,
    ]
    for func in funcs:
        logger.debug(f"exec {func.__name__}")
        res = func(str(response.url), response)
        if res[0]:
            logger.debug(f"exec {func.__name__} returned {res[1]}")
            return res

    return False, False


class WAFDetected(Exception):
    pass


def is_archived_repo(url: str, *, client: Optional[httpx.Client] = None) -> Result:
    if client is None:
        client = global_client

    try:
        response = client.get(url, follow_redirects=True)
        if _is_cloudflare_captcha(response):
            return Result(
                comfirmed=False,
                error=WAFDetected("Cloudflare WAF detected"),
                real_src=str(response.url),
            )

        if response.status_code == 404:
            return not_found_handler(response)

        if response.status_code != 200:
            return Result(
                comfirmed=False,
                error=Exception(f"HTTP status code: {response.status_code}"),
                real_src=str(response.url),
            )

        _result = check_all(response)
        return Result(
            comfirmed=_result[0],
            repo_archived=_result[1],
            real_src=str(response.url),
            error=Exception(
                "Unknown git/svn service or archive repository not supported"
            )
            if _result == (False, False)
            else None,
        )
    except Exception as e:
        return Result(comfirmed=False, error=e)


def argparser():
    import argparse

    parser = argparse.ArgumentParser(description="Check if a repository is archived")
    parser.add_argument("url", help="URL to check")

    return parser


def main():
    args = argparser().parse_args()
    pprint.pprint(is_archived_repo(args.url))


if __name__ == "__main__":
    main()
