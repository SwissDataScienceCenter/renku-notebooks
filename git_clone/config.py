import os
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


# os.environ["GIT_CLONE_MOUNT_PATH"] = "/dsfds/fds/f"
# os.environ["GIT_CLONE_REPOSITORY_URL"] = "http://repo-urls.com"
# os.environ["GIT_CLONE_LFS_AUTO_FETCH"] = "1"
# os.environ["GIT_CLONE_COMMIT_SHA"] = "fdsfdsafasfafsaf34344t"
# os.environ["GIT_CLONE_BRANCH"] = "master"
# os.environ["GIT_CLONE_RENKU_USERNAME"] = "master"
# os.environ["GIT_CLONE_GIT_AUTOSAVE"] = "master"
# os.environ["GIT_CLONE_GIT_URL"] = "master"
# os.environ["GIT_CLONE_GIT_OAUTH_TOKEN"] = "master"
# print(config_from_env().renku_username)
