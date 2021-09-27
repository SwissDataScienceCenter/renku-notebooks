import os
from werkzeug.serving import run_simple

from git_rpc_server.server import application

if __name__ == "__main__":
    run_simple(os.getenv("HOST"), 4000, application)
