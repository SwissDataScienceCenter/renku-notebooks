import json
import logging
import random
import re
import string
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from shutil import disk_usage
from urllib.parse import urljoin, urlparse

import requests

from git_services.cli import GitCLI, GitCommandError
from git_services.init import errors
from git_services.init.config import Provider, User
from git_services.init.config import Repository as ConfigRepo


@dataclass
class Repository:
    """Information required to clone a repository."""

    url: str
    dirname: str
    absolute_path: Path
    provider: str | None
    branch: str | None = None
    commit_sha: str | None = None
    _git_cli: GitCLI | None = None

    @classmethod
    def from_config_repo(cls, data: ConfigRepo, mount_path: Path):
        dirname = data.dirname or cls._make_dirname(data.url)
        provider = data.provider
        branch = data.branch
        commit_sha = data.commit_sha
        return cls(
            url=data.url,
            dirname=dirname,
            absolute_path=mount_path / dirname,
            provider=provider,
            branch=branch,
            commit_sha=commit_sha,
        )

    @property
    def git_cli(self) -> GitCLI:
        if not self._git_cli:
            if not self.absolute_path.exists():
                logging.info(f"{self.absolute_path} does not exist, creating it.")
                self.absolute_path.mkdir(parents=True, exist_ok=True)

            self._git_cli = GitCLI(self.absolute_path)

        return self._git_cli

    def exists(self) -> bool:
        try:
            is_inside = self.git_cli.git_rev_parse("--is-inside-work-tree")
        except GitCommandError:
            return False
        return is_inside.lower().strip() == "true"

    @staticmethod
    def _make_dirname(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or parsed.hostname or ""
        path = path.removesuffix(".git").removesuffix("/")
        dirname = path.rsplit("/", maxsplit=1).pop()
        if dirname:
            return dirname
        suffix = "".join([random.choice(string.ascii_lowercase + string.digits) for _ in range(3)])  # nosec B311
        return f"repo-{suffix}"


@dataclass
class GitCloner:
    mount_path: Path
    git_providers: dict[str, Provider]
    user: User
    repositories: list[Repository]
    lfs_auto_fetch: bool = False
    is_git_proxy_enabled: bool = False
    proxy_url: str = "http://localhost:8080"
    remote_name = "origin"
    remote_origin_prefix = f"remotes/{remote_name}"
    _access_tokens: dict[str, str | None] = field(default_factory=dict, repr=False)

    def _initialize_repo(self, repository: Repository):
        logging.info("Initializing repo")

        repository.git_cli.git_init()

        # NOTE: For anonymous sessions email and name are not known for the user
        if self.user.email is not None:
            logging.info(f"Setting email {self.user.email} in git config")
            repository.git_cli.git_config("user.email", self.user.email)
        if self.user.full_name is not None:
            logging.info(f"Setting name {self.user.full_name} in git config")
            repository.git_cli.git_config("user.name", self.user.full_name)
        repository.git_cli.git_config("push.default", "simple")

    @staticmethod
    def _exclude_storages_from_git(repository: Repository, storages: list[str]):
        """Git ignore cloud storage mount folders."""
        if not storages:
            return

        with open(repository.absolute_path / ".git" / "info" / "exclude", "a") as exclude_file:
            exclude_file.write("\n")

            for storage in storages:
                storage_path = Path(storage)
                if repository.absolute_path not in storage_path.parents:
                    # The storage path is not inside the repo, no need to gitignore
                    continue
                exclude_path = storage_path.relative_to(repository.absolute_path).as_posix()
                exclude_file.write(f"{exclude_path}\n")

    def _get_access_token(self, provider_id: str):
        if provider_id in self._access_tokens:
            return self._access_tokens[provider_id]
        if provider_id not in self.git_providers:
            return None

        provider = self.git_providers[provider_id]
        request_url = provider.access_token_url
        headers = {"Authorization": f"bearer {self.user.renku_token}"}
        logging.info(f"Requesting token for provider {provider_id}")
        res = requests.get(request_url, headers=headers)
        if res.status_code != 200:
            logging.warning(f"Could not get access token for provider {provider_id}")
            if provider_id in self._access_tokens:
                del self._access_tokens[provider_id]
            return None
        token = res.json()
        logging.info(f"Got token response for {provider_id}")
        self._access_tokens[provider_id] = token["access_token"]
        return self._access_tokens[provider_id]

    @contextmanager
    def _temp_plaintext_credentials(self, repository: Repository, git_user: str, git_access_token: str):
        # NOTE: If "lfs." is included in urljoin it does not work properly
        lfs_auth_setting = "lfs." + urljoin(f"{repository.url}/", "info/lfs.access")
        credential_loc = Path("/tmp/git-credentials")
        try:
            with open(credential_loc, "w") as f:
                git_host = urlparse(repository.url).netloc
                f.write(f"https://{git_user}:{git_access_token}@{git_host}")
            # NOTE: This is required to let LFS know that it should use basic auth to pull data.
            # If not set LFS will try to pull data without any auth and will then set this field
            # automatically but the password and username will be required for every git
            # operation. Setting this option when basic auth is used to clone with the context
            # manager and then unsetting it prevents getting in trouble when the user is in the
            # session by having this setting left over in the session after initialization.
            repository.git_cli.git_config(lfs_auth_setting, "basic")
            yield repository.git_cli.git_config("credential.helper", f"store --file={credential_loc}")
        finally:
            # NOTE: Temp credentials MUST be cleaned up on context manager exit
            logging.info("Cleaning up git credentials after cloning.")
            credential_loc.unlink(missing_ok=True)
            try:
                repository.git_cli.git_config("--unset", "credential.helper")
                repository.git_cli.git_config("--unset", lfs_auth_setting)
            except GitCommandError as err:
                # INFO: The repo is fully deleted when an error occurs so when the context
                # manager exits then this results in an unnecessary error that masks the true
                # error, that is why this is ignored.
                logging.warning(
                    "Git plaintext credentials were deleted but could not be "
                    "unset in the repository's config, most likely because the repository has "
                    f"been deleted. Detailed error: {err}"
                )

    @staticmethod
    def _get_lfs_total_size_bytes(repository: Repository) -> int:
        """Get the total size of all LFS files in bytes."""
        try:
            res = repository.git_cli.git_lfs("ls-files", "--json")
        except GitCommandError:
            return 0
        res_json = json.loads(res)
        size_bytes = 0
        files = res_json.get("files", [])
        if not files:
            return 0
        for f in files:
            size_bytes += f.get("size", 0)
        return size_bytes

    @staticmethod
    def _get_default_branch(repository: Repository, remote_name: str) -> str:
        """Get the default branch of the repository."""
        try:
            repository.git_cli.git_remote("set-head", remote_name, "--auto")
            res = repository.git_cli.git_symbolic_ref(f"refs/remotes/{remote_name}/HEAD")
        except GitCommandError as err:
            raise errors.BranchDoesNotExistError from err
        r = re.compile(r"^refs/remotes/origin/(?P<branch>.*)$")
        match = r.match(res)
        if match is None:
            raise errors.BranchDoesNotExistError
        match_dict = match.groupdict()
        return match_dict["branch"]

    def _clone(self, repository: Repository):
        logging.info(f"Cloning repository {repository.dirname} from {repository.url}")
        if self.lfs_auto_fetch:
            repository.git_cli.git_lfs("install", "--local")
        else:
            repository.git_cli.git_lfs("install", "--skip-smudge", "--local")
        repository.git_cli.git_remote("add", self.remote_name, repository.url)
        try:
            repository.git_cli.git_fetch(self.remote_name)
        except GitCommandError as err:
            raise errors.GitFetchError from err
        branch = repository.branch or self._get_default_branch(repository=repository, remote_name=self.remote_name)
        logging.info(f"Checking out branch {branch}")
        try:
            repository.git_cli.git_checkout(branch)
        except GitCommandError as err:
            if err.returncode != 0 or len(err.stderr) != 0:
                if "no space left on device" in str(err.stderr).lower():
                    # INFO: not enough disk space
                    raise errors.NoDiskSpaceError from err
                else:
                    raise errors.BranchDoesNotExistError from err
        if self.lfs_auto_fetch:
            total_lfs_size_bytes = self._get_lfs_total_size_bytes(repository)
            _, _, free_space_bytes = disk_usage(repository.absolute_path.as_posix())
            if free_space_bytes < total_lfs_size_bytes:
                raise errors.NoDiskSpaceError
            repository.git_cli.git_lfs("install", "--local")
            repository.git_cli.git_lfs("pull")
        try:
            logging.info("Dealing with submodules")
            repository.git_cli.git_submodule("init")
            repository.git_cli.git_submodule("update")
        except GitCommandError as err:
            logging.error(msg="Couldn't initialize submodules", exc_info=err)

    def run(self, storage_mounts: list[str]):
        for repository in self.repositories:
            self.run_helper(repository, storage_mounts=storage_mounts)

    def run_helper(self, repository: Repository, *, storage_mounts: list[str]):
        logging.info("Checking if the repo already exists.")
        if repository.exists():
            # NOTE: This will run when a session is resumed, removing the repo here
            # will result in lost work if there is uncommitted work.
            logging.info("The repo already exists - updating git proxy config.")
            # TODO
            return

        # TODO: Is this something else for non-GitLab providers?
        git_user = "oauth2"
        git_access_token = self._get_access_token(repository.provider) if repository.provider else None

        self._initialize_repo(repository)
        try:
            if self.user.is_anonymous or git_access_token is None:
                self._clone(repository)
            else:
                with self._temp_plaintext_credentials(repository, git_user, git_access_token):
                    self._clone(repository)
            if repository.commit_sha:
                repository.git_cli.git_reset("--hard", repository.commit_sha)
        except errors.GitFetchError as err:
            logging.error(msg=f"Cannot clone {repository.url}", exc_info=err)
            with open(repository.absolute_path / "ERROR", mode="w", encoding="utf-8") as f:
                import traceback

                traceback.print_exception(err, file=f)
            return
        except errors.BranchDoesNotExistError as err:
            logging.error(msg=f"Error while cloning {repository.url}", exc_info=err)

        # NOTE: If the storage mount location already exists it means that the repo folder/file
        # or another existing file will be overwritten, so raise an error here and crash.
        for a_mount in storage_mounts:
            if Path(a_mount).exists():
                raise errors.CloudStorageOverwritesExistingFilesError

        logging.info(f"Excluding cloud storage from git: {storage_mounts} for {repository}")
        if storage_mounts:
            self._exclude_storages_from_git(repository, storage_mounts)

        self._setup_proxy(repository)

    def _setup_proxy(self, repository: Repository):
        if not self.is_git_proxy_enabled:
            logging.info("Skipping git proxy setup")
            return
        logging.info(f"Setting up git proxy to {self.proxy_url}")
        repository.git_cli.git_config("http.proxy", self.proxy_url)
        repository.git_cli.git_config("http.sslVerify", "false")
