import pytest

from git_clone.git_cli import GitCommandError


def test_git_config(init_git_repo):
    git_cli = init_git_repo()
    email = "test.email@sdsc.com"
    git_cli.git_config(f"--local user.email {email}")
    with open(git_cli.repo_directory / ".git" / "config", "r") as f:
        config = f.read()
    assert email in config


def test_git_push(init_git_repo):
    git_cli = init_git_repo()
    with pytest.raises(GitCommandError) as exc_info:
        git_cli.git_push()
    assert exc_info.value.returncode != 0
    assert "No configured push destination" in exc_info.value.stderr


def test_git_submodule(init_git_repo):
    git_cli = init_git_repo()
    git_cli.git_submodule("add --depth 1 https://github.com/SwissDataScienceCenter/renku.git")
    assert (git_cli.repo_directory / "renku").exists()


def test_git_checkout(init_git_repo, make_branch):
    git_cli = init_git_repo()
    new_branch = "new_branch"
    git_cli.git_checkout(f"-b {new_branch}")
    assert new_branch in git_cli.git_branch("--show-current")


def test_git_lfs(init_git_repo):
    git_cli = init_git_repo()
    lfs_file = "file1.bin"
    git_cli.git_lfs(f"track {lfs_file}")
    assert (git_cli.repo_directory / ".gitattributes").exists()
    with open(git_cli.repo_directory / ".gitattributes", "r") as f:
        contents = f.read()
    assert lfs_file in contents

# def test_git_branch(self, command=""):
#     return self._execute_command("git branch " + command)

# def test_git_remote(self, command=""):
#     return self._execute_command("git remote " + command)

# def test_git_reset(self, command=""):
#     return self._execute_command("git reset " + command)

# def test_git_fetch(self, command=""):
#     return self._execute_command("git fetch " + command)

# def test_git_rev_parse(self, command=""):
#     return self._execute_command("git rev-parse " + command)

# def test_git_init(self, command=""):
#     return self._execute_command("git init " + command)
