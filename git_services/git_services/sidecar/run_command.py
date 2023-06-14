import argparse
from git_services.sidecar.config import config_from_env
from git_services.sidecar.commands.base import shutdown_git_proxy
from git_services.cli.sentry import setup_sentry

if __name__ == "__main__":
    config = config_from_env()
    setup_sentry(config.sentry)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        metavar="COMMAND",
        type=str,
        choices=["shutdown_git_proxy"],
        help="The command to execute",
    )
    args = parser.parse_args()

    if args.command == "shutdown_git_proxy":
        shutdown_git_proxy(git_proxy_health_port=config.git_proxy_health_port)
