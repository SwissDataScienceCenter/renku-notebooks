import sys

from git_services.init import errors
from git_services.init.cloner import GitCloner
from git_services.init.config import config_from_env

# NOTE: register exception handler
sys.excepthook = errors.handle_exception

if __name__ == "__main__":
    config = config_from_env()
    git_cloner = GitCloner(
        config.git_url,
        config.repository_url,
        config.user,
        config.lfs_auto_fetch == "1",
        config.mount_path,
    )
    git_cloner.run(config.git_autosave == "1", config.branch, config.commit_sha)
