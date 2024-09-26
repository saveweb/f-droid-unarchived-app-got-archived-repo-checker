from dataclasses import dataclass
from typing import Optional

import httpx

@dataclass
class Result:
    confirmed: bool
    """ is the result reliable """
    repo_deleted: bool
    repo_archived: bool
    moved_to: Optional[str]
    repo_real: str
    """ the real URL after redirects """
    error: Optional[Exception]
    def __init__(
        self,
        *,
        repo_deleted: Optional[bool] = None,
        repo_archived: Optional[bool] = None,
        moved_to: Optional[str] = None,
        real_src: str = "",
        error: Optional[Exception] = None,
    ):
        self.confirmed = repo_deleted != None or repo_archived != None or moved_to != None
        self.repo_deleted = repo_deleted or False
        self.repo_archived = repo_archived or False
        self.moved_to = moved_to
        self.repo_real = real_src
        self.error = error


global_client = httpx.Client(
    http2=True,
    headers={
        "User-Agent": "is_archived_repo/0.1.0 (is_archived_repo checker)",
        "language": "en-US,en;q=0.5",
    },
    timeout=5,
)
