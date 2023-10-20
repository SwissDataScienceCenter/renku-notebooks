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
    git_cloner = GitCloner(
        config.git_url,
        config.repository_url,
        config.user,
        config.lfs_auto_fetch,
        config.mount_path,
    )
    git_cloner.run(
        session_branch=config.branch,
        root_commit_sha=config.commit_sha,
        s3_mounts=config.s3_mounts,
    )
