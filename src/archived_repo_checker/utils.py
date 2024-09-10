from dataclasses import dataclass
from typing import Optional

import httpx

@dataclass
class Result:
    comfirmed: bool
    """ is the result reliable """
    repo_deleted: bool
    repo_archived: bool
    src_real: str
    """ the real URL after redirects """
    error: Optional[Exception]
    def __init__(
        self,
        *,
        comfirmed: bool = False,
        repo_deleted: bool = False,
        repo_archived: bool = False,
        real_src: str = "",
        error: Optional[Exception] = None,
    ):
        self.comfirmed = comfirmed
        self.repo_deleted = repo_deleted
        self.repo_archived = repo_archived
        self.src_real = real_src
        self.error = error


global_client = httpx.Client(
    http2=True,
    headers={
        "User-Agent": "is_archived_repo/0.1.0 (is_archived_repo checker)",
        "language": "en-US,en;q=0.5",
    },
    timeout=5,
)
