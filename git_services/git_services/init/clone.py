import sys

from git_services.init import errors
from git_services.init.cloner import GitCloner, User
from git_services.init.config import config_from_env

# NOTE: register exception handler
sys.excepthook = errors.handle_exception

if __name__ == "__main__":
    config = config_from_env()
    user = User(
        config.renku_username,
        config.git_full_name,
        config.git_email,
        config.git_oauth_token,
    )
    git_cloner = GitCloner(
        config.git_url,
        config.repository_url,
        user,
        config.lfs_auto_fetch,
        config.mount_path,
    )
    git_cloner.run(config.git_autosave, config.branch, config.commit_sha)
