import argparse
from git_services.sidecar.config import config_from_env
from git_services.sidecar.rpc_server import autosave
from git_services.cli.sentry import setup_sentry

if __name__ == "__main__":
    config = config_from_env()
    setup_sentry(config.sentry)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        metavar="COMMAND",
        type=str,
        choices=["autosave"],
        help="The command to execute",
    )
    args = parser.parse_args()

    if args.command == "autosave":
        autosave(
            path=config.mount_path, git_proxy_health_port=config.git_proxy_health_port
        )
