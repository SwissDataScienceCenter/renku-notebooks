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
    git_autosave: bool = "0"
    lfs_auto_fetch: bool = "0"
    mount_path: str = "/work"

    def __post_init__(self):
        self.lfs_auto_fetch = self.lfs_auto_fetch == "1"
        self.git_autosave = self.git_autosave == "1"


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
