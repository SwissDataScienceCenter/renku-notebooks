import shlex
from dataclasses import dataclass, field
from pathlib import Path

import dataconf

from git_services.cli.sentry import SentryConfig
from git_services.init import errors


@dataclass
class User:
    """Class for keep track of basic user info used in cloning a repo."""

    username: str
    internal_gitlab_access_token: str | None = None
    full_name: str | None = None
    email: str | None = None
    renku_token: str | None = None

    def __post_init__(self):
        # NOTE: Sanitize user input that is used in running git shell commands with shlex
        # NOTE: shlex.quote(None) == "''"
        if self.full_name is not None:
            self.full_name = shlex.quote(self.full_name)
        if self.email is not None:
            self.email = shlex.quote(self.email)

    @property
    def is_anonymous(self) -> bool:
        return not self.renku_token


@dataclass
class Repository:
    """Represents a git repository."""

    url: str
    branch: str | None = None
    commit_sha: str | None = None


@dataclass
class Provider:
    """Represents a git provider."""

    id: str
    access_token: str


@dataclass
class Config:
    sentry: SentryConfig
    repositories: list[Repository] = field(default_factory=list)
    workspace_mount_path: str = None
    git_providers: list[Provider] = field(default_factory=list)
    internal_gitlab_url: str = None
    user: User = None
    lfs_auto_fetch: str | bool = "0"
    mount_path: str = "/work"
    storage_mounts: list[str] = field(default_factory=list)

    def __post_init__(self):
        allowed_string_flags = ["0", "1"]
        if isinstance(self.lfs_auto_fetch, str) and self.lfs_auto_fetch not in allowed_string_flags:
            raise ValueError("lfs_auto_fetch can only be a string with values '0' or '1'")
        if isinstance(self.lfs_auto_fetch, str):
            self.lfs_auto_fetch = self.lfs_auto_fetch == "1"
        for mount in self.storage_mounts:
            if not Path(mount).is_absolute():
                raise errors.CloudStorageMountPathNotAbsolute


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
