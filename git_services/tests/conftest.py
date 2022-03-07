from pathlib import Path
import pytest
import shutil

from git_services.cli import GitCLI


@pytest.fixture
def git_cli(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    yield GitCLI(repo_dir)
    shutil.rmtree(repo_dir, ignore_errors=False)


@pytest.fixture
def create_file(git_cli):
    def _create_file(name: Path, contents: str):
        print("Creating files in create file")
        print(f"Creating file {git_cli.repo_directory / name}")
        with open(git_cli.repo_directory / name, "w") as f:
            f.write(contents)

    return _create_file


@pytest.fixture
def commit_everything(git_cli):
    def _commit_everything():
        print("Commiting everything")
        git_cli._execute_command("git add .")
        git_cli._execute_command("git commit -m 'test commit'")

    return _commit_everything


@pytest.fixture
def make_branch():
    def _make_branch(git_cli, name):
        git_cli.git_checkout(f"-b {name}")

    return _make_branch


@pytest.fixture
def init_git_repo(git_cli, create_file, commit_everything):
    def _init_git_repo():
        git_cli.git_init()
        print("Creating files in init git repo")
        create_file("file1", "Sample file 1")
        create_file("file2", "Sample file 2")
        commit_everything()
        return git_cli

    return _init_git_repo


@pytest.fixture
def git_repo_with_user(init_git_repo):
    git_cli = init_git_repo()

    email = "test.email@sdsc.com"
    git_cli.git_config(f"--local user.email {email}")
    name = "Renku User"
    git_cli.git_config(f"--local user.name {name}")
    yield git_cli
