import os
from jsonrpc import dispatcher
from werkzeug.serving import run_simple

from git_rpc_server.server import application
from git_rpc_server.methods import git, resources


if __name__ == "__main__":
    # Add all methods
    dispatcher.add_method(git.status, "git/status")
    dispatcher.add_method(resources.disk_usage, "resources/diskUsage")
    # Run server
    run_simple(os.getenv("HOST"), 4000, application)
