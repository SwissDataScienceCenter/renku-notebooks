import pytest

from renku_notebooks.api.classes.k8s_client import (
    JsServerCache,
    NamespacedK8sClient,
    K8sClient,
)
from renku_notebooks.errors.intermittent import JSCacheError
from renku_notebooks.errors.programming import ProgrammingError


@pytest.fixture
def mock_server_cache(mocker):
    server_cache = mocker.MagicMock(JsServerCache)
    return server_cache


@pytest.fixture
def mock_namespaced_client(mocker):
    def _mock_namespaced_client(namespace):
        mock_client = mocker.MagicMock(NamespacedK8sClient)
        mock_client.namespace = namespace
        return mock_client

    yield _mock_namespaced_client


def test_list_failed_cache(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest = {
        "metadata": {"labels": {"username": "username"}, "name": "server1"}
    }
    mock_server_cache.list_servers.side_effect = JSCacheError()
    renku_ns_client.list_servers.return_value = []
    sessions_ns_client.list_servers.return_value = [sample_server_manifest]
    client = K8sClient(
        mock_server_cache, renku_ns_client, "username", sessions_ns_client
    )
    servers = client.list_servers("username")
    assert servers == [sample_server_manifest]


def test_list_cache_preference(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest = {
        "metadata": {"labels": {"username": "username"}, "name": "server1"}
    }
    sample_server_manifest_preferred = {
        "metadata": {"labels": {"username": "username"}, "name": "preferred"}
    }
    mock_server_cache.list_servers.return_value = [sample_server_manifest_preferred]
    renku_ns_client.list_servers.return_value = []
    sessions_ns_client.list_servers.return_value = [sample_server_manifest]
    client = K8sClient(
        mock_server_cache, renku_ns_client, "username", sessions_ns_client
    )
    servers = client.list_servers("username")
    assert servers == [sample_server_manifest_preferred]


def test_list_single_namespace(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    mock_server_cache.list_servers.side_effect = JSCacheError()
    sample_server_manifest = {
        "metadata": {"labels": {"username": "username"}, "name": "server1"}
    }
    renku_ns_client.list_servers.return_value = [sample_server_manifest]
    client = K8sClient(mock_server_cache, renku_ns_client, username_label="username")
    servers = client.list_servers("username")
    assert servers == [sample_server_manifest]


def test_get_failed_cache(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest = {
        "metadata": {"labels": {"username": "username"}, "name": "server1"}
    }
    mock_server_cache.get_server.side_effect = JSCacheError()
    renku_ns_client.get_server.return_value = sample_server_manifest
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(
        mock_server_cache, renku_ns_client, "username", sessions_ns_client
    )
    server = client.get_server("server", "username")
    assert server == sample_server_manifest


def test_get_two_results_raises_error(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.side_effect = JSCacheError()
    sample_server_manifest1 = {
        "metadata": {"labels": {"username": "username"}, "name": "server1"}
    }
    sample_server_manifest2 = {
        "metadata": {"labels": {"username": "username"}, "name": "server2"}
    }
    renku_ns_client.get_server.return_value = sample_server_manifest1
    sessions_ns_client.get_server.return_value = sample_server_manifest2
    client = K8sClient(
        mock_server_cache, renku_ns_client, "username", sessions_ns_client
    )
    with pytest.raises(ProgrammingError):
        client.get_server("server", "username")


def test_get_cache_is_preferred(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest_cache = {
        "metadata": {"labels": {"username": "username"}, "name": "server"}
    }
    sample_server_manifest_non_cache = {
        "metadata": {
            "labels": {"username": "username", "not_preferred": True},
            "name": "server",
        }
    }
    mock_server_cache.get_server.return_value = sample_server_manifest_cache
    renku_ns_client.get_server.return_value = sample_server_manifest_non_cache
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(
        mock_server_cache, renku_ns_client, "username", sessions_ns_client
    )
    server = client.get_server("server", "username")
    assert server == sample_server_manifest_cache


def test_get_server_no_match(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.return_value = None
    renku_ns_client.get_server.return_value = "non_cache_server"
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(
        mock_server_cache, renku_ns_client, "username", sessions_ns_client
    )
    server = client.get_server("server", "username")
    assert server is None
