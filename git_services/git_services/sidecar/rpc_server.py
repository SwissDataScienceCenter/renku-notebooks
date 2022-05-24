from contextlib import contextmanager
import json
from jsonrpc import JSONRPCResponseManager, dispatcher as jsonrpc_dispatcher
import os
import requests
from werkzeug.wrappers import Response, Request
from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from pathlib import Path
from subprocess import PIPE, Popen
import shlex

from git_services.cli import GitCLI
from git_services.cli.sentry import setup_sentry
from git_services.sidecar.config import config_from_env


def status(path: str = os.environ.get("MOUNT_PATH", "."), **kwargs):
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


def health_app(environ, start_response):
    response = Response(json.dumps({"status": "running"}), status=200, mimetype='application/json')
    return response(environ, start_response)


def autosave(**kwargs):
    """Create an autosave branch with uncommitted work."""
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
        git_proxy_health_port = os.getenv("GIT_PROXY_HEALTH_PORT", "8081")
        repo_path = os.environ.get("MOUNT_PATH")
        status_result = status(path=repo_path)
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

        cli = GitCLI(Path(repo_path))

        cli.git_checkout(f"-b {autosave_branch_name}")

        if should_commit:
            # INFO: Find large files that should be checked in git LFS
            autosave_min_file_size = os.getenv("AUTOSAVE_MINIMUM_LFS_FILE_SIZE_BYTES", "1000000")
            cmd_res = Popen(
                shlex.split(f"find . -type f -size +{autosave_min_file_size}c"),
                cwd=Path(repo_path),
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


def application(request):
    """Listen for incoming requests on /jsonrpc"""
    response = JSONRPCResponseManager.handle(request.data, jsonrpc_dispatcher)
    return Response(response.json, mimetype="application/json")


if __name__ == "__main__":
    config = config_from_env()
    setup_sentry(config.sentry)
    jsonrpc_dispatcher.add_method(status, "git/get_status")
    jsonrpc_dispatcher.add_method(autosave, "autosave/create")
    jsonrpc_app = Request.application(application)
    app = DispatcherMiddleware(
        jsonrpc_app,
        {f"{config.url_prefix}health": health_app},
    )
    run_simple(config.host, config.port, app)
