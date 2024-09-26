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


def check_all(response: httpx.Response) -> Result:
    funcs = [
        methods.github_check,
        methods.gitlab_check,
        methods.gitea_check,
        methods.gitee_check,
    ]
    res = Result()
    for func in funcs:
        logger.debug(f"exec {func.__name__}")
        res = func(str(response.url), response)
        if res.confirmed:
            logger.debug(f"exec {func.__name__} returned {res.repo_archived}")
            break

    return res


class WAFDetected(Exception):
    pass


def is_archived_repo(url: str, *, client: Optional[httpx.Client] = None) -> Result:
    if client is None:
        client = global_client

    try:
        response = client.get(url, follow_redirects=True)
        if _is_cloudflare_captcha(response):
            return Result(
                error=WAFDetected("Cloudflare WAF detected"),
                real_src=str(response.url),
            )

        if response.status_code == 404:
            return not_found_handler(response)

        if response.status_code != 200:
            return Result(
                error=Exception(f"HTTP status code: {response.status_code}"),
                real_src=str(response.url),
            )

        result = check_all(response)
        result.real_src = str(response.url),
        if not result.confirmed:
            result.error = Exception("Unknown git/svn service or archive repository not supported")
        return result
    except Exception as e:
        return Result(error=e)


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
