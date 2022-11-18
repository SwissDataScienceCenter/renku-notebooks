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
    mock_server_cache.list_servers.side_effect = JSCacheError()
    renku_ns_client.list_servers.return_value = []
    sessions_ns_client.list_servers.return_value = ["server1"]
    client = K8sClient(mock_server_cache, renku_ns_client, sessions_ns_client)
    servers = client.list_servers("username")
    assert servers == ["server1"]


def test_list_cache_preference(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.list_servers.return_value = ["preference"]
    renku_ns_client.list_servers.return_value = []
    sessions_ns_client.list_servers.return_value = ["server1"]
    client = K8sClient(mock_server_cache, renku_ns_client, sessions_ns_client)
    servers = client.list_servers("username")
    assert servers == ["preference"]


def test_list_single_namespace(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    mock_server_cache.list_servers.side_effect = JSCacheError()
    renku_ns_client.list_servers.return_value = ["server1"]
    client = K8sClient(mock_server_cache, renku_ns_client)
    servers = client.list_servers("username")
    assert servers == ["server1"]


def test_get_failed_cache(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.side_effect = JSCacheError()
    renku_ns_client.get_server.return_value = "server1"
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(mock_server_cache, renku_ns_client, sessions_ns_client)
    server = client.get_server("server")
    assert server == "server1"


def test_get_two_results_raises_error(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.side_effect = JSCacheError()
    renku_ns_client.get_server.return_value = "server1"
    sessions_ns_client.get_server.return_value = "server2"
    client = K8sClient(mock_server_cache, renku_ns_client, sessions_ns_client)
    with pytest.raises(ProgrammingError):
        client.get_server("server")


def test_get_cache_is_preferred(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.return_value = "cache_server"
    renku_ns_client.get_server.return_value = "non_cache_server"
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(mock_server_cache, renku_ns_client, sessions_ns_client)
    server = client.get_server("server")
    assert server == "cache_server"


def test_get_server_no_match(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.return_value = None
    renku_ns_client.get_server.return_value = "non_cache_server"
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(mock_server_cache, renku_ns_client, sessions_ns_client)
    server = client.get_server("server")
    assert server is None
