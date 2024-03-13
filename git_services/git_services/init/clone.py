import json
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
        repository_url = repos[0]["url"]
    else:
        repository_url = config.repository_url

    git_cloner = GitCloner(
        repositories=json.loads(config.repositories) if config.repositories else [],
        workspace_mount_path=config.workspace_mount_path,
        user=config.user,
        lfs_auto_fetch=config.lfs_auto_fetch,
        repository_url=repository_url,
    )
    git_cloner.run(storage_mounts=config.storage_mounts)
