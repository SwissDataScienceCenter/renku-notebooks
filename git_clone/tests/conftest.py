from pathlib import Path
import pytest
import shutil

from git_clone.git_cli import GitCLI


@pytest.fixture
def git_cli(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    yield GitCLI(repo_dir)
    shutil.rmtree(repo_dir, ignore_errors=False)


@pytest.fixture
def create_file():
    def _create_file(name: Path, contents: str):
        with open(name, "w") as f:
            f.write(contents)
        yield name
        name.unlink()

    return _create_file


@pytest.fixture
def commit_everything(git_cli: GitCLI):
    def _commit_everything():
        git_cli._execute_command("git add .")
        git_cli._execute_command("git commit -m 'test commit'")

    return _commit_everything


@pytest.fixture
def make_branch():
    def _make_branch(git_cli, name):
        git_cli.git_checkout(f"-b {name}")
        yield name

    return _make_branch


@pytest.fixture
def init_git_repo(git_cli, create_file, commit_everything):
    def _init_git_repo():
        git_cli.git_init()
        create_file("file1", "Sample file 1")
        create_file("file2", "Sample file 2")
        commit_everything
        return git_cli

    return _init_git_repo
