from subprocess import check_output


def status(**kwargs):
    """Execute \"git status\" on the repository."""
    status = check_output(["git", "status"]).decode("utf-8")

    repo_clean = True
    for keyword in ["ahead", "modified", "untracked"]:
        if keyword in status:
            repo_clean = False

    return {"clean": repo_clean, "status": status}
