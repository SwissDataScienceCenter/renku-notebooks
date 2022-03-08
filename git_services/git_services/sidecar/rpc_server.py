from git_services.sidecar.config import config_from_env
from jsonrpc import JSONRPCResponseManager, dispatcher
import os
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
from pathlib import Path
from git_services.cli import GitCLI
from git_services.cli.sentry import setup_sentry


@dispatcher.add_method
def status(path: str = ".", **kwargs):
    """Execute \"git status\" on the repository."""
    cli = GitCLI(Path(path))
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


@dispatcher.add_method
def autosave(**kwargs):
    """Create an autosave branch with uncommitted work."""
    repo_path = os.environ.get("MOUNT_PATH")
    status_result = status(path=repo_path)
    should_commit = not status_result["clean"]
    should_push = status_result["ahead"] > 0

    if not should_commit and not should_push:
        return

    initial_commit = os.environ["CI_COMMIT_SHA"][0:7]
    current_commit = status_result["commit"][0:7]
    current_branch = status_result["branch"]

    user = os.environ["RENKU_USERNAME"]

    autosave_branch_name = (
        f"renku/autosave/{user}/{current_branch}/{initial_commit}/{current_commit}"
    )

    cli = GitCLI(Path(repo_path))

    cli.git_checkout(f"-b {autosave_branch_name}")

    if should_commit:
        cli.git_add("-A")
        cli.git_commit(
            f"--no-verify -m 'Auto-saving for {user} on branch {current_branch} from commit {initial_commit}'"
        )

    cli.git_push(f"origin {autosave_branch_name}")

    cli.git_reset(f"--soft {current_branch}")
    cli.git_checkout(f"{current_branch}")
    cli.git_branch(f"-D {autosave_branch_name}")


@Request.application
def application(request):
    """Listen for incoming requests on /jsonrpc"""
    response = JSONRPCResponseManager.handle(request.data, dispatcher)
    return Response(response.json, mimetype="application/json")


if __name__ == "__main__":
    config = config_from_env()
    setup_sentry(config.sentry)

    run_simple(os.getenv("HOST"), 4000, application)
