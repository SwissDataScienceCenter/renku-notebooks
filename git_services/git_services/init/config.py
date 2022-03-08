# import os
from dataclasses import dataclass
import dataconf
from typing import Optional


@dataclass
class Config:
    repository_url: str
    commit_sha: str
    branch: str
    renku_username: str
    git_url: str
    git_oauth_token: str
    git_email: Optional[str]
    git_full_name: Optional[str]
    git_autosave: bool = "0"
    lfs_auto_fetch: bool = "0"
    mount_path: str = "/work"

    def __post_init__(self):
        self.lfs_auto_fetch = self.lfs_auto_fetch == "1"
        self.git_autosave = self.git_autosave == "1"


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
