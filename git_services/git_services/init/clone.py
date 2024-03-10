import json
import logging
import sys

from git_services.cli.sentry import setup_sentry
from git_services.init import errors
from git_services.init.cloner import GitCloner
from git_services.init.config import config_from_env

# NOTE: register exception handler
sys.excepthook = errors.handle_exception

if __name__ == "__main__":
    config = config_from_env()
    setup_sentry(config.sentry)

    repositories = config.repositories
    if repositories:
        repos = json.loads(repositories)
        branch = repos[0]["branch"]
        commit_sha = repos[0]["commit_sha"]
        repository_url = repos[0]["url"]
    else:
        branch = config.branch
        commit_sha = config.commit_sha
        repository_url = config.repository_url

    logging.basicConfig(level=logging.INFO)
    logging.warning(f"RENKU 2 {config.workspace_mount_path} {config.mount_path} {config.git_url}")
    logging.warning(f"RENKU 2 {bool(repositories)} {branch} {commit_sha} {repository_url}")

    git_cloner = GitCloner(
        git_url=config.git_url,
        repo_url=config.repository_url,
        user=config.user,
        lfs_auto_fetch=config.lfs_auto_fetch,
        repo_directory=config.mount_path,
    )
    git_cloner.run(
        session_branch=config.branch,
        root_commit_sha=config.commit_sha,
        storage_mounts=config.storage_mounts,
    )
