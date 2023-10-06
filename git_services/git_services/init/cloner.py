import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from shutil import disk_usage
from time import sleep
from typing import List
from urllib.parse import urljoin, urlparse

import requests

from git_services.cli import GitCLI, GitCommandError
from git_services.init import errors
from git_services.init.config import User


class GitCloner:
    remote_name = "origin"
    remote_origin_prefix = f"remotes/{remote_name}"
    proxy_url = "http://localhost:8080"

    def __init__(
        self,
        git_url,
        repo_url,
        user: User,
        lfs_auto_fetch=False,
        repo_directory=".",
    ):
        logging.basicConfig(level=logging.INFO)
        self.git_url = git_url
        self.repo_url = repo_url
        self.repo_directory = Path(repo_directory)
        if not self.repo_directory.exists():
            logging.info(f"{self.repo_directory} does not exist, creating it.")
            self.repo_directory.mkdir(parents=True, exist_ok=True)
        self.cli = GitCLI(self.repo_directory)
        self.user = user
        self.git_host = urlparse(git_url).netloc
        self.lfs_auto_fetch = lfs_auto_fetch
        self._wait_for_server()

    def _wait_for_server(self, timeout_mins=None):
        start = datetime.now()

        while True:
            logging.info(f"Waiting for git to become available with timeout mins {timeout_mins}...")
            res = requests.get(self.git_url)
            if 200 <= res.status_code < 400:
                logging.info("Git is available")
                return
            if timeout_mins is not None:
                timeout_delta = timedelta(minutes=timeout_mins)
                if datetime.now() - start > timeout_delta:
                    raise errors.GitServerUnavailableError
            sleep(5)

    def _initialize_repo(self):
        logging.info("Initializing repo")
        self.cli.git_init()
        # NOTE: For anonymous sessions email and name are not known for the user
        if self.user.email is not None:
            logging.info(f"Setting email {self.user.email} in git config")
            self.cli.git_config("user.email", self.user.email)
        if self.user.full_name is not None:
            logging.info(f"Setting name {self.user.full_name} in git config")
            self.cli.git_config("user.name", self.user.full_name)
        self.cli.git_config("push.default", "simple")

    def _setup_proxy(self):
        logging.info(f"Setting up git proxy to {self.proxy_url}")
        self.cli.git_config("http.proxy", self.proxy_url)
        self.cli.git_config("http.sslVerify", "false")

    def _exclude_storages_from_git(self, storages: List[str]):
        """Git ignore cloud storage mount folders."""
        first = True
        with open(self.repo_directory / ".git" / "info" / "exclude", "a") as exclude_file:
            for storage in storages:
                if first:
                    prefix = "\n"
                    first = False
                else:
                    prefix = ""
                    path = Path(storage).relative_to(self.repo_directory).as_posix()
                    exclude_file.write(f"{prefix}{path}\n")

    @contextmanager
    def _temp_plaintext_credentials(self):
        # NOTE: If "lfs." is included in urljoin it does not work properly
        lfs_auth_setting = "lfs." + urljoin(f"{self.repo_url}/", "info/lfs.access")
        credential_loc = Path("/tmp/git-credentials")
        try:
            with open(credential_loc, "w") as f:
                f.write(f"https://oauth2:{self.user.oauth_token}@{self.git_host}")
            # NOTE: This is required to let LFS know that it should use basic auth to pull data.
            # If not set LFS will try to pull data without any auth and will then set this field
            # automatically but the password and username will be required for every git
            # operation. Setting this option when basic auth is used to clone with the context
            # manager and then unsetting it prevents getting in trouble when the user is in the
            # session by having this setting left over in the session after initialization.
            self.cli.git_config(lfs_auth_setting, "basic")
            yield self.cli.git_config("credential.helper", f"store --file={credential_loc}")
        finally:
            # NOTE: Temp credentials MUST be cleaned up on context manager exit
            logging.info("Cleaning up git credentials after cloning.")
            credential_loc.unlink(missing_ok=True)
            try:
                self.cli.git_config("--unset", "credential.helper")
                self.cli.git_config("--unset", lfs_auth_setting)
            except GitCommandError as err:
                # INFO: The repo is fully deleted when an error occurs so when the context
                # manager exits then this results in an unnecessary error that masks the true
                # error, that is why this is ignored.
                logging.warning(
                    "Git plaintext credentials were deleted but could not be "
                    "unset in the repository's config, most likely because the repository has "
                    f"been deleted. Detailed error: {err}"
                )

    def _get_lfs_total_size_bytes(self) -> int:
        """Get the total size of all LFS files in bytes."""
        try:
            res = self.cli.git_lfs("ls-files", "--json")
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

    def _clone(self, branch):
        logging.info(f"Cloning branch {branch}")
        if self.lfs_auto_fetch:
            self.cli.git_lfs("install", "--local")
        else:
            self.cli.git_lfs("install", "--skip-smudge", "--local")
        self.cli.git_remote("add", self.remote_name, self.repo_url)
        self.cli.git_fetch(self.remote_name)
        try:
            self.cli.git_checkout(branch)
        except GitCommandError as err:
            if err.returncode != 0 or len(err.stderr) != 0:
                if "no space left on device" in str(err.stderr).lower():
                    # INFO: not enough disk space
                    raise errors.NoDiskSpaceError from err
                else:
                    raise errors.BranchDoesNotExistError from err
        if self.lfs_auto_fetch:
            total_lfs_size_bytes = self._get_lfs_total_size_bytes()
            _, _, free_space_bytes = disk_usage(self.cli.repo_directory)
            if free_space_bytes < total_lfs_size_bytes:
                raise errors.NoDiskSpaceError
            self.cli.git_lfs("install", "--local")
            self.cli.git_lfs("pull")
        try:
            logging.info("Dealing with submodules")
            self.cli.git_submodule("init")
            self.cli.git_submodule("update")
        except GitCommandError as err:
            logging.error(msg="Couldn't initialize submodules", exc_info=err)

    def _repo_exists(self):
        try:
            res = self.cli.git_rev_parse("--is-inside-work-tree")
        except GitCommandError:
            return False
        return res.lower().strip() == "true"

    def run(self, *, session_branch, root_commit_sha, s3_mount):
        logging.info("Checking if the repo already exists.")
        if self._repo_exists():
            logging.info("The repo already exists - exiting.")
            return
        self._initialize_repo()
        if self.user.is_anonymous:
            self._clone(session_branch)
            self.cli.git_reset("--hard", root_commit_sha)
        else:
            with self._temp_plaintext_credentials():
                self._clone(session_branch)
        self._setup_proxy()
        logging.info(f"Excluding cloud storage from git: {s3_mount}")
        if s3_mount:
            self._exclude_storages_from_git(s3_mount)
