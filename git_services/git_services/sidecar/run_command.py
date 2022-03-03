import argparse
from git_services.sidecar.rpc_server import autosave

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", metavar="COMMAND", type=str, choices=["autosave"], help="The command to execute")
    args = parser.parse_args()

    if args.command == "autosave":
        autosave()