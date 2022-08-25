from urllib.parse import urljoin

import pytest

from git_services.cli import GitCLI
from git_services.sidecar.app import get_app
from git_services.sidecar.config import Config, config_from_env
from git_services.sidecar.errors import JSONRPCGenericError


@pytest.fixture()
def setup_env(monkeypatch):
    monkeypatch.setenv("GIT_RPC_SENTRY__ENABLED", "False")


@pytest.fixture()
def rpc_config(setup_env):
    return config_from_env()


@pytest.fixture()
def app(setup_env):
    app = get_app()
    app.config.update(
        {
            "TESTING": True,
            "DEBUG": True,
        }
    )

    yield app


@pytest.fixture()
def test_client(app):
    return app.test_client()


@pytest.fixture()
def project_git_cli(init_git_repo, monkeypatch):
    git_cli: GitCLI = init_git_repo(init_renku=True)
    monkeypatch.setenv("GIT_RPC_MOUNT_PATH", git_cli.repo_directory)
    return git_cli


def test_version_check(test_client, rpc_config: Config):
    health_url = urljoin(rpc_config.url_prefix, "health")
    res = test_client.get(health_url, follow_redirects=True)
    assert res.status_code == 200
    assert "running" in res.text


def test_rpc_docs(test_client, rpc_config: Config):
    health_url = urljoin(rpc_config.url_prefix, "jsonrpc/map")
    res = test_client.get(health_url, follow_redirects=True)
    assert res.status_code == 200
    assert "JSON-RPC map" in res.text


def test_status_dirty(project_git_cli: GitCLI, test_client, rpc_config: Config):
    with open(project_git_cli.repo_directory / "unsaved-file.txt", "w") as f:
        f.write("Test")
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={"id": 0, "jsonrpc": "2.0", "method": "git/get_status"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert not res.json.get("result", {}).get("clean", True)


def test_status_clean(project_git_cli: GitCLI, test_client, rpc_config: Config):
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={"id": 0, "jsonrpc": "2.0", "method": "git/get_status"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert res.json.get("result", {}).get("clean", False)


def test_invalid_renku_command(project_git_cli: GitCLI, test_client, rpc_config: Config):
    command_name = "test"
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "renku/run",
            "params": {"command_name": command_name},
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert f"Command {command_name} is not recognized" in res.json["error"]["message"]


def test_valid_renku_save(project_git_cli: GitCLI, test_client, rpc_config: Config):
    command_name = "save"
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "renku/run",
            "params": {"command_name": command_name},
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    # NOTE: A GitError means that the renku save command executed as expected and
    # only failed at the last step before the git push is executed triggers the error below.
    assert "GitError" in res.json["error"]["message"]


def test_error_endpoint(test_client, rpc_config: Config):
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "dummy/get_error",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert res.json["error"]["message"] == JSONRPCGenericError().error.message
    assert res.json["error"]["code"] == JSONRPCGenericError().error.code


@pytest.mark.parametrize("committed_changes", [True, False])
def test_discard_unsaved_changes(
    test_client, rpc_config: Config, clone_git_repo, committed_changes
):
    url = "https://github.com/SwissDataScienceCenter/renku.git"
    git_cli: GitCLI = clone_git_repo(url)
    with open(git_cli.repo_directory / "test.txt", "w") as f:
        f.write("test")
    assert (git_cli.repo_directory / "test.txt").exists()
    if committed_changes:
        git_cli.git_add(".")
        git_cli.git_commit("-m 'testing discard'")
        assert "testing discard" in git_cli._execute_command("git log")
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "git/discard_unsaved_changes",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert res.json["result"] is None
    assert not (git_cli.repo_directory / "test.txt").exists()
    if committed_changes:
        assert "testing discard" not in git_cli._execute_command("git log")


def test_pull_no_conflicts(test_client, rpc_config: Config, clone_git_repo):
    url = "https://github.com/SwissDataScienceCenter/renku.git"
    git_cli: GitCLI = clone_git_repo(url)
    latest_sha = git_cli.git_rev_parse("HEAD")
    git_cli.git_reset("--hard HEAD~1")
    assert git_cli.git_rev_parse("HEAD") != latest_sha
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "git/pull",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert res.json["result"] is None
    assert latest_sha == git_cli.git_rev_parse("HEAD")


def test_pull_conflicts(test_client, rpc_config: Config, clone_git_repo):
    url = "https://github.com/SwissDataScienceCenter/renku.git"
    git_cli: GitCLI = clone_git_repo(url)
    latest_sha = git_cli.git_rev_parse("HEAD")
    git_cli.git_reset("--hard HEAD~1")
    assert git_cli.git_rev_parse("HEAD") != latest_sha
    with open(git_cli.repo_directory / "README.rst", "w") as f:
        f.write("Test introduce conflict")
    git_cli.git_add("README.rst")
    git_cli.git_commit("-m testing")
    res = test_client.post(
        urljoin(rpc_config.url_prefix, "jsonrpc"),
        json={
            "id": 0,
            "jsonrpc": "2.0",
            "method": "git/pull",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Not possible to fast-forward" in res.json["error"]["message"]
    assert git_cli.git_rev_parse("HEAD") != latest_sha
