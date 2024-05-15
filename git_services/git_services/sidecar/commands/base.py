from pathlib import Path

from renku.command.command_builder.command import Command

from git_services.cli import GitCLI
from git_services.sidecar.errors import SidecarUserError
from git_services.sidecar.renku_cli_config import RenkuCommandName, renku_cli_config


def status(path: Path):
    """Execute 'git status --porcelain=v2 --branch' on the repository.

    Args:
    ----
        path (str): The location of the repository.

    Returns:
    -------
        dict: A dictionary with several keys:
        'clean': boolean indicating if the repository is clean
        'ahead': integer indicating how many commits the local repo is ahead of the remote
        'behind': integer indicating how many commits the local repo is behind of the remote
        'branch': string with the name of the current branch
        'commit': string with the current commit SHA
        'status': string with the 'raw' result from running git status in the repository

    """
    cli = GitCLI(path)
    cli.git_fetch()
    status = cli.git_status("--porcelain=v2", "--branch")

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


def discard_unsaved_changes(path: Path):
    """Completely discard any changes that have not been pushed to the remote repository."""
    cli = GitCLI(path)
    cli.git_fetch("--all")
    remote_sha = cli.git_rev_parse("@{u}").strip()
    cli.git_reset("--hard", remote_sha)
    cli.git_clean("-fd")


def pull(path: Path, fast_forward_only: bool = True):
    """Run fetch and pull on the repository."""
    cli = GitCLI(path)
    cli.git_fetch("--all")
    if fast_forward_only:
        cli.git_pull("--ff-only")
    else:
        cli.git_pull("--ff")
