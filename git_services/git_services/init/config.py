from dataclasses import dataclass
import dataconf
from typing import Optional

from git_services.cli.sentry import SentryConfig


@dataclass
class User:
    """Class for keep track of basic user info used in cloning a repo."""

    username: str
    oauth_token: str
    full_name: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Config:
    repository_url: str
    commit_sha: str
    branch: str
    git_url: str
    user: User
    sentry: SentryConfig
    git_autosave: str = "0"
    lfs_auto_fetch: str = "0"
    mount_path: str = "/work"
    s3_mount: str = ""

    def __post_init__(self):
        allowed_string_flags = ["0", "1"]
        if self.git_autosave not in allowed_string_flags:
            raise ValueError("git_autosave can only be a string with values '0' or '1'")
        if self.lfs_auto_fetch not in allowed_string_flags:
            raise ValueError("lfs_auto_fetch can only be a string with values '0' or '1'")


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
