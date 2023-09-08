from dataclasses import dataclass
import dataconf
import shlex
from typing import Optional, Union, List

from git_services.cli.sentry import SentryConfig


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
    repository_url: str
    commit_sha: str
    branch: str
    git_url: str
    user: User
    sentry: SentryConfig
    git_autosave: Union[str, bool] = "0"
    lfs_auto_fetch: Union[str, bool] = "0"
    mount_path: str = "/work"
    s3_mount: List[str] = []

    def __post_init__(self):
        allowed_string_flags = ["0", "1"]
        if self.git_autosave not in allowed_string_flags:
            raise ValueError("git_autosave can only be a string with values '0' or '1'")
        if self.lfs_auto_fetch not in allowed_string_flags:
            raise ValueError(
                "lfs_auto_fetch can only be a string with values '0' or '1'"
            )
        if isinstance(self.git_autosave, str):
            self.git_autosave = self.git_autosave == "1"
        if isinstance(self.lfs_auto_fetch, str):
            self.lfs_auto_fetch = self.lfs_auto_fetch == "1"


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
