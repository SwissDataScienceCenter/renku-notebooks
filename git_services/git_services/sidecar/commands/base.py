import os
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, Popen
import shlex

from renku.command.command_builder.command import Command
import requests

from git_services.cli import GitCLI
from git_services.sidecar.errors import SidecarUserError
from git_services.sidecar.renku_cli_config import renku_cli_config, RenkuCommandName


def status(path: Path):
    """Execute \"git status --porcelain=v2 --branch\" on the repository.

    Args:
        path (str): The location of the repository.

    Returns:
        dict: A dictionary with several keys:
        'clean': boolean indicating if the repository is clean
        'ahead': integer indicating how many commits the local repo is ahead of the remote
        'behind': integer indicating how many commits the local repo is behind of the remote
        'branch': string with the name of the current branch
        'commit': string with the current commit SHA
        'status': string with the 'raw' result from running git status in the repository
    """
    cli = GitCLI(path)
    status = cli.git_status("--porcelain=v2 --branch")

    repo_clean = True

    ahead = 0
    behind = 0
    current_branch = ""
    current_commit = ""

    ahead_behind_prefix = "# branch.ab "
    branch_prefix = "# branch.head "
    commit_prefix = "# branch.oid "

    for line in status.splitlines():
        if len(line) == 0:
            continue

        if line.startswith(ahead_behind_prefix):
            ahead, behind = line[len(ahead_behind_prefix) :].split(" ")
            ahead = int(ahead[1:])
            behind = int(behind[1:])
        elif line.startswith(branch_prefix):
            current_branch = line[len(branch_prefix) :]
        elif line.startswith(commit_prefix):
            current_commit = line[len(commit_prefix) :]
        elif line[0] in ["1", "2", "?"]:
            repo_clean = False

    return {
        "clean": repo_clean,
        "ahead": ahead,
        "behind": behind,
        "branch": current_branch,
        "commit": current_commit,
        "status": status,
    }


def autosave(path: Path, git_proxy_health_port: int):
    """Create an autosave branch with uncommitted work and push it to the remote."""

    @contextmanager
    def _shutdown_git_proxy_when_done():
        """Inform the git-proxy it can shut down.
        The git-proxy will wait for this in order to shutdown.
        If this "shutdown" call does not happen then the proxy will ignore SIGTERM signals
        and shutdown after a specific long period (i.e. 10 minutes)."""
        try:
            yield None
        finally:
            requests.get(f"http://localhost:{git_proxy_health_port}/shutdown")

    with _shutdown_git_proxy_when_done():
        status_result = status(path=path)
        should_commit = not status_result["clean"]
        should_push = status_result["ahead"] > 0

        if not (should_commit or should_push):
            return

        initial_commit = os.environ["CI_COMMIT_SHA"][0:7]
        current_commit = status_result["commit"][0:7]
        current_branch = status_result["branch"]

        user = os.environ["RENKU_USERNAME"]

        autosave_branch_name = (
            f"renku/autosave/{user}/{current_branch}/{initial_commit}/{current_commit}"
        )

        cli = GitCLI(path)

        cli.git_checkout(f"-b {autosave_branch_name}")

        if should_commit:
            # INFO: Find large files that should be checked in git LFS
            autosave_min_file_size = os.getenv(
                "AUTOSAVE_MINIMUM_LFS_FILE_SIZE_BYTES", "1000000"
            )
            cmd_res = Popen(
                shlex.split(f"find . -type f -size +{autosave_min_file_size}c"),
                cwd=path,
                stdout=PIPE,
                stderr=PIPE,
            )
            stdout, _ = cmd_res.communicate()
            lfs_files = stdout.decode("utf-8").split()
            if len(lfs_files) > 0:
                cli.git_lfs("track " + " ".join(lfs_files))
            cli.git_add("-A")
            cli.git_commit(
                "--no-verify "
                f"-m 'Auto-saving for {user} on branch "
                f"{current_branch} from commit {initial_commit}'"
            )

        cli.git_push(f"origin {autosave_branch_name}")

        cli.git_reset(f"--soft {current_branch}")
        cli.git_checkout(f"{current_branch}")
        cli.git_branch(f"-D {autosave_branch_name}")
        return autosave_branch_name


def renku(path: Path, command_name: str, **kwargs):
    """Run a renku command in the session repository."""
    try:
        command_enum = RenkuCommandName[command_name]
    except KeyError:
        raise SidecarUserError(
            message=f"Command {command_name} is not recognized, allowed commands "
            f"are {', '.join(RenkuCommandName.get_all_names())}."
        )
    command = renku_cli_config[command_enum]
    command_builder: Command = command.command()
    command_builder.working_directory(str(path.absolute()))
    command_builder.build()
    output = command_builder.execute(**kwargs)
    return command.output_serializer(output)
