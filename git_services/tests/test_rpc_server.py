from urllib.parse import urljoin

import pytest

from git_services.cli import GitCLI
from git_services.sidecar.app import get_app
from git_services.sidecar.config import Config, config_from_env


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
    assert f"Command {command_name} is not recognized" in res.json["error"]["data"]["message"]


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
    # NOTE: A remote is not setup so git push fails, but that means that the renku save command
    # executed as expected and only fail at the last step which triggers the error below.
    assert (
        res.json["error"]["data"]["message"] == "No remote has been set up for the current branch"
    )
