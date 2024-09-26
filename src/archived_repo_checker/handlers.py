import httpx

from archived_repo_checker.utils import Result

not_found_is_deleted_hosts = [
    "github.com",
    "gitlab.com",
    "codeberg.org",
    "bitbucket.org",
    "sourceforge.net"
    "sr.ht",
]

def not_found_handler(r: httpx.Response) -> Result:
    for host in not_found_is_deleted_hosts:
        if host in r.url.host:
            return Result(repo_deleted=True, repo_real=str(r.url), error=Exception(f"HTTP status code: {r.status_code}"))
    return Result(repo_real=str(r.url), error=Exception(f"HTTP status code: {r.status_code}"))
