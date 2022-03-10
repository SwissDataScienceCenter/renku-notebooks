# import os
from dataclasses import dataclass
import dataconf


@dataclass
class User:
    """Class for keep track of basic user info used in cloning a repo."""

    username: str
    oauth_token: str
    full_name: str = None
    email: str = None


@dataclass
class Config:
    repository_url: str
    commit_sha: str
    branch: str
    git_url: str
    user: User
    git_autosave: str = "0"
    lfs_auto_fetch: str = "0"
    mount_path: str = "/work"

    def __post_init__(self):
        allowed_string_flags = ["0", "1"]
        if self.git_autosave not in allowed_string_flags:
            raise ValueError("git_autosave can only be a string with values '0' or '1'")
        if self.lfs_auto_fetch not in allowed_string_flags:
            raise ValueError("lfs_auto_fetch can only be a string with values '0' or '1'")


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
