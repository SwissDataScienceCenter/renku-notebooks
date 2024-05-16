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
    provider: str | None = None
    dirname: str | None = None
    branch: str | None = None
    commit_sha: str | None = None


@dataclass
class Provider:
    """Represents a git provider."""

    id: str
    access_token_url: str


@dataclass
class Config:
    sentry: SentryConfig
    workspace_mount_path: str
    mount_path: str
    user: User
    repositories: list[Repository] = field(default_factory=list)
    git_providers: list[Provider] = field(default_factory=list)
    lfs_auto_fetch: str | bool = "0"
    storage_mounts: list[str] = field(default_factory=list)
    is_git_proxy_enabled: str | bool = "0"

    def __post_init__(self):
        self._check_bool_flag("lfs_auto_fetch")
        self._check_bool_flag("is_git_proxy_enabled")
        for mount in self.storage_mounts:
            if not Path(mount).is_absolute():
                raise errors.CloudStorageMountPathNotAbsolute

    def _check_bool_flag(self, attr: str):
        value = getattr(self, attr)
        if isinstance(value, bool):
            return
        allowed_string_flags = ["0", "1"]
        if value not in allowed_string_flags:
            raise ValueError(f"{attr} can only be a string with values '0' or '1'")
        setattr(self, attr, value == "1")


def config_from_env() -> Config:
    return dataconf.env("GIT_CLONE_", Config)
