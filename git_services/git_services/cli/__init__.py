from pathlib import Path
import shlex
import os


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

    def _execute_command(self, command: str, **kwargs):
        # NOTE: When running in gunicorn with gevent Popen and PIPE from subprocess do not work
        # and the gevent equivalents have to be used
        if os.environ.get("RUNNING_WITH_GEVENT"):
            from gevent.subprocess import Popen, PIPE
        else:
            from subprocess import Popen, PIPE
        args = shlex.split(command)
        res = Popen(args, stdout=PIPE, stderr=PIPE, cwd=self.repo_directory, **kwargs)
        stdout, stderr = res.communicate()
        if type(stdout) is bytes:
            stdout = stdout.decode()
        if type(stderr) is bytes:
            stderr = stderr.decode()
        if len(stderr) > 0 and res.returncode != 0:
            raise GitCommandError(res.returncode, stdout, stderr)
        return stdout

    def git_config(self, command=""):
        return self._execute_command("git config " + command)

    def git_push(self, command=""):
        return self._execute_command("git push " + command)

    def git_submodule(self, command=""):
        return self._execute_command("git submodule " + command)

    def git_checkout(self, command=""):
        return self._execute_command("git checkout " + command)

    def git_lfs(self, command=""):
        return self._execute_command("git lfs " + command)

    def git_branch(self, command=""):
        return self._execute_command("git branch " + command)

    def git_remote(self, command=""):
        return self._execute_command("git remote " + command)

    def git_reset(self, command=""):
        return self._execute_command("git reset " + command)

    def git_fetch(self, command=""):
        return self._execute_command("git fetch " + command)

    def git_rev_parse(self, command=""):
        return self._execute_command("git rev-parse " + command)

    def git_init(self, command=""):
        return self._execute_command("git init " + command)

    def git_status(self, command=""):
        return self._execute_command("git status " + command)

    def git_add(self, command=""):
        return self._execute_command("git add " + command)

    def git_commit(self, command=""):
        return self._execute_command("git commit " + command)

    def git_clean(self, command=""):
        return self._execute_command("git clean " + command)

    def git_pull(self, command=""):
        return self._execute_command("git pull " + command)

    def git_clone(self, command=""):
        return self._execute_command("git clone " + command)
