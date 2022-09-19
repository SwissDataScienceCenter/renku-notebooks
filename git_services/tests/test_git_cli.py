from pathlib import Path
import pytest

from git_services.cli import GitCommandError


@pytest.mark.parametrize(
    "email,username",
    [
        ("test.email@sdsc.com", "test name"),
        ("test.email@sdsc.com", "|| exit(1)"),
        ("test.email@sdsc.com", "Something 'weird''"),
        ("test.email@sdsc.com", "--Something"),
        ("test.email@sdsc.com", "Æë😄"),
    ],
)
def test_git_config(init_git_repo, email, username):
    git_cli = init_git_repo()
    email = "test.email@sdsc.com"
    git_cli.git_config("--local", "user.email", email)
    git_cli.git_config("--local", "user.name", username)
    with open(git_cli.repo_directory / ".git" / "config", "r") as f:
        config = f.read()
    assert email in config
    assert username in config


def test_git_push(init_git_repo):
    git_cli = init_git_repo()
    with pytest.raises(GitCommandError) as exc_info:
        git_cli.git_push()
    assert exc_info.value.returncode != 0
    assert "No configured push destination" in exc_info.value.stderr


def test_git_submodule(init_git_repo):
    git_cli = init_git_repo()
    git_cli.git_submodule(
        "add", "--depth", "1", "https://github.com/SwissDataScienceCenter/renku.git"
    )
    assert (git_cli.repo_directory / "renku").exists()


def test_git_checkout(init_git_repo):
    git_cli = init_git_repo()
    new_branch = "new_branch"
    git_cli.git_checkout("-b", new_branch)
    assert new_branch in git_cli.git_branch("--show-current")


def test_git_lfs(init_git_repo):
    git_cli = init_git_repo()
    lfs_file = "file1.bin"
    git_cli.git_lfs("track", lfs_file)
    assert (git_cli.repo_directory / ".gitattributes").exists()
    with open(git_cli.repo_directory / ".gitattributes", "r") as f:
        contents = f.read()
    assert lfs_file in contents


def test_git_branch(init_git_repo):
    git_cli = init_git_repo()
    branch_name = "test-new-branch"
    git_cli.git_branch(branch_name)
    assert branch_name in git_cli.git_branch("-a")


def test_git_remote(init_git_repo):
    git_cli = init_git_repo()
    remote_name = "origin"
    remote_url = "https://renkulab.io/gitlab/project"
    git_cli.git_remote("add", remote_name, remote_url)
    remotes = git_cli.git_remote("-v")
    assert remote_name in remotes
    assert remote_url in remotes


def test_git_reset(init_git_repo, create_file, commit_everything):
    git_cli = init_git_repo()
    new_file = "another-new-file.txt"
    create_file(Path(new_file), "some content")
    commit_0 = git_cli.git_rev_parse("HEAD")
    commit_everything()
    commit_1 = git_cli.git_rev_parse("HEAD")
    assert commit_0 != commit_1
    git_cli.git_reset("--hard", "HEAD^1")
    assert git_cli.git_rev_parse("HEAD") == commit_0
