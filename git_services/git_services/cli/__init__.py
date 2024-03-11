import os
from pathlib import Path


class GitCommandError(Exception):
    def __init__(self, returncode, stdout, stderr) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RepoDirectoryDoesNotExistError(Exception):
    pass


class GitCLI:
    def __init__(self, repo_directory: Path) -> None:
        self.repo_directory = repo_directory
        if not self.repo_directory.exists():
            raise RepoDirectoryDoesNotExistError

    def _execute_command(self, *args):
        # NOTE: When running in gunicorn with gevent Popen and PIPE from subprocess do not work
        # and the gevent equivalents have to be used

        print("RENKU 2 RUNNING WITH", *args)

        if os.environ.get("RUNNING_WITH_GEVENT"):
            from gevent.subprocess import PIPE, Popen
        else:
            from subprocess import PIPE, Popen
        res = Popen(args, stdout=PIPE, stderr=PIPE, cwd=self.repo_directory)
        stdout, stderr = res.communicate()
        if type(stdout) is bytes:
            stdout = stdout.decode()
        if type(stderr) is bytes:
            stderr = stderr.decode()
        if len(stderr) > 0 and res.returncode != 0:
            raise GitCommandError(res.returncode, stdout, stderr)
        return stdout

    def git_config(self, *args):
        return self._execute_command("git", "config", *args)

    def git_push(self, *args):
        return self._execute_command("git", "push", *args)

    def git_submodule(self, *args):
        return self._execute_command("git", "submodule", *args)

    def git_checkout(self, *args):
        return self._execute_command("git", "checkout", *args)

    def git_lfs(self, *args):
        return self._execute_command("git", "lfs", *args)

    def git_branch(self, *args):
        return self._execute_command("git", "branch", *args)

    def git_remote(self, *args):
        return self._execute_command("git", "remote", *args)

    def git_reset(self, *args):
        return self._execute_command("git", "reset", *args)

    def git_fetch(self, *args):
        return self._execute_command("git", "fetch", *args)

    def git_rev_parse(self, *args):
        return self._execute_command("git", "rev-parse", *args)

    def git_init(self, *args):
        return self._execute_command("git", "init", *args)

    def git_status(self, *args):
        return self._execute_command("git", "status", *args)

    def git_add(self, *args):
        return self._execute_command("git", "add", *args)

    def git_commit(self, *args):
        return self._execute_command("git", "commit", *args)

    def git_clean(self, *args):
        return self._execute_command("git", "clean", *args)

    def git_pull(self, *args):
        return self._execute_command("git", "pull", *args)

    def git_clone(self, *args):
        return self._execute_command("git", "clone", *args)

    def git_diff(self, *args):
        return self._execute_command("git", "diff", *args)
