from jsonrpc import JSONRPCResponseManager, dispatcher
import os
from subprocess import check_output
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple


# We currently work on only one repo, the path to this
# repo is 'hardcoded' through the environment variable.
os.chdir(os.environ.get("MOUNT_PATH"))


@dispatcher.add_method
def status(**kwargs):
    """Execute \"git status\" on the repository."""
    status = check_output(["git", "status"]).decode("utf-8")

    repo_clean = True
    for keyword in ["ahead", "modified", "untracked"]:
        if keyword in status:
            repo_clean = False

    return {"clean": repo_clean, "status": status}


@Request.application
def application(request):
    """Listen for incoming requests on /jsonrpc"""
    response = JSONRPCResponseManager.handle(request.data, dispatcher)
    return Response(response.json, mimetype="application/json")


if __name__ == "__main__":
    run_simple(os.getenv("HOST"), 4000, application)
