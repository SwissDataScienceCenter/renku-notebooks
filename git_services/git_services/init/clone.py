import logging
import sys
from pathlib import Path
from typing import cast

from git_services.cli.sentry import setup_sentry
from git_services.init import errors
from git_services.init.cloner import GitCloner, Repository
from git_services.init.config import config_from_env

# NOTE: register exception handler
sys.excepthook = errors.handle_exception

if __name__ == "__main__":
    config = config_from_env()
    setup_sentry(config.sentry)
    logging.basicConfig(level=logging.INFO)
    base_path = Path(config.mount_path)

    git_cloner = GitCloner(
        repositories=[Repository.from_config_repo(r, mount_path=base_path) for r in config.repositories],
        git_providers={p.id: p for p in config.git_providers},
        mount_path=base_path,
        user=config.user,
        lfs_auto_fetch=cast(bool, config.lfs_auto_fetch),
        is_git_proxy_enabled=cast(bool, config.is_git_proxy_enabled),
        proxy_url=f"http://localhost:{config.git_proxy_port}"
    )
    git_cloner.run(storage_mounts=config.storage_mounts)
