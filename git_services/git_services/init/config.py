import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import dataconf

from git_services.cli.sentry import SentryConfig
from git_services.init import errors


@dataclass
class User:
    """Class for keep track of basic user info used in cloning a repo."""

    username: str
    oauth_token: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None

    def __post_init__(self):
        # NOTE: Sanitize user input that is used in running git shell commands with shlex
        # NOTE: shlex.quote(None) == "''"
        if self.full_name is not None:
            self.full_name = shlex.quote(self.full_name)
        if self.email is not None:
            self.email = shlex.quote(self.email)

    @property
    def is_anonymous(self) -> bool:
        return self.oauth_token is None or self.oauth_token == ""


@dataclass
class Config:
    sentry: SentryConfig
    repository_url: str = None
    commit_sha: str = None
    branch: str = None
    git_url: str = None
    user: User = None
    lfs_auto_fetch: Union[str, bool] = "0"
    mount_path: str = "/work"
    storage_mounts: List[str] = field(default_factory=list)

    def __post_init__(self):
        allowed_string_flags = ["0", "1"]
        if self.lfs_auto_fetch not in allowed_string_flags:
            raise ValueError("lfs_auto_fetch can only be a string with values '0' or '1'")
        if isinstance(self.lfs_auto_fetch, str):
            self.lfs_auto_fetch = self.lfs_auto_fetch == "1"
        for mount in self.storage_mounts:
            if not Path(mount).is_absolute():
                raise errors.CloudStorageMountPathNotAbsolute


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
