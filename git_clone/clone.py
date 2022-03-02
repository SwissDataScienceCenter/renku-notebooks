import sys

import errors
from git_cloner import GitCloner, User
from config import config_from_env

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
    git_cloner.clone_and_recover(config.git_autosave, config.branch, config.commit_sha)
