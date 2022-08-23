from contextlib import contextmanager
import requests
from datetime import datetime, timedelta
import json
import logging
from time import sleep
from pathlib import Path
import re
from shutil import disk_usage
from urllib.parse import urlparse

from git_services.init import errors
from git_services.cli import GitCLI, GitCommandError
from git_services.init.config import User


class GitCloner:
    remote_name = "origin"
    remote_origin_prefix = f"remotes/{remote_name}"
    autosave_branch_prefix = "renku/autosave"
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
        repo_directory = Path(repo_directory)
        if not repo_directory.exists():
            logging.info(f"{repo_directory} does not exist, creating it.")
            repo_directory.mkdir(parents=True, exist_ok=True)
        self.cli = GitCLI(repo_directory)
        self.user = user
        self.git_host = urlparse(git_url).netloc
        self.lfs_auto_fetch = lfs_auto_fetch
        self._wait_for_server()

    def _wait_for_server(self, timeout_mins=None):
        start = datetime.now()

        while True:
            logging.info(
                f"Waiting for git to become available with timeout mins {timeout_mins}..."
            )
            res = requests.get(self.git_url)
            if res.status_code >= 200 and res.status_code < 400:
                logging.info("Git is available")
                return
            if timeout_mins is not None:
                timeout_tdelta = timedelta(minutes=timeout_mins)
                if datetime.now() - start > timeout_tdelta:
                    raise errors.GitServerUnavailableError
            sleep(5)

    def _initialize_repo(self):
        logging.info(
            f"Intitializing repo with email {self.user.email} and name {self.user.full_name}"
        )
        self.cli.git_init()
        # NOTE: For anonymous sessions email and name are not known for the user
        if self.user.email is not None:
            self.cli.git_config(f"user.email '{self.user.email}'")
        if self.user.full_name is not None:
            self.cli.git_config(f"user.name '{self.user.full_name}'")
        self.cli.git_config("push.default simple")

    def _setup_proxy(self):
        logging.info(f"Setting up git proxy to {self.proxy_url}")
        self.cli.git_config(f"http.proxy {self.proxy_url}")
        self.cli.git_config("http.sslVerify false")

    @contextmanager
    def _temp_plaintext_credentials(self):
        try:
            credential_loc = Path("/tmp/git-credentials")
            with open(credential_loc, "w") as f:
                f.write(f"https://oauth2:{self.user.oauth_token}@{self.git_host}")
            yield self.cli.git_config(
                f"credential.helper 'store --file={credential_loc}'"
            )
        finally:
            # NOTE: Temp credentials MUST be cleaned up on context manager exit
            logging.info("Cleaning up git credentials after cloning.")
            credential_loc.unlink(missing_ok=True)
            try:
                self.cli.git_config("--unset credential.helper")
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
            res = self.cli.git_lfs("ls-files --json")
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
        self.cli.git_lfs("install --skip-smudge --local")
        self.cli.git_remote(f"add {self.remote_name} {self.repo_url}")
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
            self.cli.git_lfs("install --local")
            self.cli.git_lfs("pull")
        try:
            logging.info("Dealing with submodules")
            self.cli.git_submodule("init")
            self.cli.git_submodule("update")
        except GitCommandError as err:
            raise errors.GitSubmoduleError from err

    def _get_autosave_branch(self, session_branch, root_commit_sha):
        logging.info("Checking for autosaves")
        if self.user.full_name is None and self.user.email is None:
            # INFO: There can be no autosaves for anonymous users
            return None
        autosave_regex = (
            f"^{self.remote_origin_prefix}/{self.autosave_branch_prefix}/"
            f"{self.user.username}/{session_branch}/{root_commit_sha[:7]}/"
            r"[a-zA-Z0-9]{7}$"
        )
        branches = self.cli.git_branch("-a").split()
        autosave = [
            branch
            for branch in branches
            if re.match(autosave_regex, branch) is not None
        ]
        if len(autosave) == 0:
            return None
        logging.info(f"Autosave found {autosave[0]}")
        return autosave[0]

    def _recover_autosave(self, autosave_branch):
        logging.info(f"Recovering autosave {autosave_branch}")
        autosave_items = autosave_branch.split("/")
        # INFO: Check if the found autosave branch has a valid format, fail otherwise
        if len(autosave_items) < 7:
            raise errors.UnexpectedAutosaveFormatError
        # INFO: Reset the file tree to the auto-saved state.
        self.cli.git_reset(f"--hard {autosave_branch}")
        # INFO: Reset HEAD to the last committed change prior to the autosave commit.
        pre_save_local_commit_sha = autosave_items[7]
        self.cli.git_reset(f"--soft {pre_save_local_commit_sha}")
        # INFO: Unstage all modified files.
        self.cli.git_reset("HEAD .")
        # INFO: Delete the autosave branch both remotely and locally.
        autosave_local_branch = "/".join(autosave_items[2:])
        logging.info(f"Recovery successful, deleting branch {autosave_local_branch}")
        self.cli.git_push(f'{self.remote_name} --delete "{autosave_local_branch}"')

    def _repo_exists(self):
        try:
            res = self.cli.git_rev_parse("--is-inside-work-tree")
        except GitCommandError:
            return False
        return res.lower().strip() == "true"

    def run(self, recover_autosave, session_branch, root_commit_sha):
        logging.info("Checking if the repo already exists.")
        if self._repo_exists():
            logging.info("The repo already exists - exiting.")
            return
        self._initialize_repo()
        with self._temp_plaintext_credentials():
            self._clone(session_branch)
            if recover_autosave:
                autosave_branch = self._get_autosave_branch(
                    session_branch, root_commit_sha
                )
                if autosave_branch is None:
                    self.cli.git_reset(f"--hard {root_commit_sha}")
                else:
                    self._recover_autosave(autosave_branch)
        self._setup_proxy()
