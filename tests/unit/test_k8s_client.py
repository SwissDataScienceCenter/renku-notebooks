import pytest
from kubernetes.client import (
    V1Container,
    V1EnvVar,
    V1EnvVarSource,
    V1LabelSelector,
    V1PodSpec,
    V1PodTemplateSpec,
    V1StatefulSet,
    V1StatefulSetSpec,
)

from renku_notebooks.api.classes.auth import RenkuTokens
from renku_notebooks.api.classes.k8s_client import JsServerCache, K8sClient, NamespacedK8sClient
from renku_notebooks.errors.intermittent import JSCacheError
from renku_notebooks.errors.programming import ProgrammingError
from renku_notebooks.util.kubernetes_ import find_env_var


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
    sample_server_manifest = {"metadata": {"labels": {"username": "username"}, "name": "server1"}}
    mock_server_cache.list_servers.side_effect = JSCacheError()
    renku_ns_client.list_servers.return_value = []
    sessions_ns_client.list_servers.return_value = [sample_server_manifest]
    client = K8sClient(mock_server_cache, renku_ns_client, "username", sessions_ns_client)
    servers = client.list_servers("username")
    assert servers == [sample_server_manifest]


def test_list_cache_preference(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest = {"metadata": {"labels": {"username": "username"}, "name": "server1"}}
    sample_server_manifest_preferred = {"metadata": {"labels": {"username": "username"}, "name": "preferred"}}
    mock_server_cache.list_servers.return_value = [sample_server_manifest_preferred]
    renku_ns_client.list_servers.return_value = []
    sessions_ns_client.list_servers.return_value = [sample_server_manifest]
    client = K8sClient(mock_server_cache, renku_ns_client, "username", sessions_ns_client)
    servers = client.list_servers("username")
    assert servers == [sample_server_manifest_preferred]


def test_list_single_namespace(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    mock_server_cache.list_servers.side_effect = JSCacheError()
    sample_server_manifest = {"metadata": {"labels": {"username": "username"}, "name": "server1"}}
    renku_ns_client.list_servers.return_value = [sample_server_manifest]
    client = K8sClient(mock_server_cache, renku_ns_client, username_label="username")
    servers = client.list_servers("username")
    assert servers == [sample_server_manifest]


def test_get_failed_cache(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest = {"metadata": {"labels": {"username": "username"}, "name": "server1"}}
    mock_server_cache.get_server.side_effect = JSCacheError()
    renku_ns_client.get_server.return_value = sample_server_manifest
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(mock_server_cache, renku_ns_client, "username", sessions_ns_client)
    server = client.get_server("server", "username")
    assert server == sample_server_manifest


def test_get_two_results_raises_error(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.side_effect = JSCacheError()
    sample_server_manifest1 = {"metadata": {"labels": {"username": "username"}, "name": "server1"}}
    sample_server_manifest2 = {"metadata": {"labels": {"username": "username"}, "name": "server2"}}
    renku_ns_client.get_server.return_value = sample_server_manifest1
    sessions_ns_client.get_server.return_value = sample_server_manifest2
    client = K8sClient(mock_server_cache, renku_ns_client, "username", sessions_ns_client)
    with pytest.raises(ProgrammingError):
        client.get_server("server", "username")


def test_get_cache_is_preferred(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    sample_server_manifest_cache = {"metadata": {"labels": {"username": "username"}, "name": "server"}}
    sample_server_manifest_non_cache = {
        "metadata": {
            "labels": {"username": "username", "not_preferred": True},
            "name": "server",
        }
    }
    mock_server_cache.get_server.return_value = sample_server_manifest_cache
    renku_ns_client.get_server.return_value = sample_server_manifest_non_cache
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(mock_server_cache, renku_ns_client, "username", sessions_ns_client)
    server = client.get_server("server", "username")
    assert server == sample_server_manifest_cache


def test_get_server_no_match(mock_server_cache, mock_namespaced_client):
    renku_ns_client = mock_namespaced_client("renku")
    sessions_ns_client = mock_namespaced_client("renku-sessions")
    mock_server_cache.get_server.return_value = None
    renku_ns_client.get_server.return_value = "non_cache_server"
    sessions_ns_client.get_server.return_value = None
    client = K8sClient(mock_server_cache, renku_ns_client, "username", sessions_ns_client)
    server = client.get_server("server", "username")
    assert server is None


def test_find_env_var():
    container = V1Container(
        name="test", env=[V1EnvVar(name="key1", value="val1"), V1EnvVar(name="key2", value_from=V1EnvVarSource())]
    )
    assert find_env_var(container, "key1") == (0, "val1")
    assert find_env_var(container, "key2") == (1, V1EnvVarSource())
    assert find_env_var(container, "missing") is None


def test_patch_statefulset_tokens():
    git_clone_access_env = "GIT_CLONE_USER__RENKU_TOKEN"
    git_proxy_access_env = "GIT_PROXY_RENKU_ACCESS_TOKEN"
    git_proxy_refresh_env = "GIT_PROXY_RENKU_REFRESH_TOKEN"
    secrets_access_env = "RENKU_ACCESS_TOKEN"
    git_clone = V1Container(
        name="git-clone",
        env=[
            V1EnvVar(name="test", value="value"),
            V1EnvVar(git_clone_access_env, "old_value"),
            V1EnvVar(name="test-from-source", value_from=V1EnvVarSource()),
        ],
    )
    git_proxy = V1Container(
        name="git-proxy",
        env=[
            V1EnvVar(name="test", value="value"),
            V1EnvVar(name="test-from-source", value_from=V1EnvVarSource()),
            V1EnvVar(git_proxy_refresh_env, "old_value"),
            V1EnvVar(git_proxy_access_env, "old_value"),
        ],
    )
    secrets = V1Container(
        name="init-user-secrets",
        env=[
            V1EnvVar(secrets_access_env, "old_value"),
            V1EnvVar(name="test", value="value"),
            V1EnvVar(name="test-from-source", value_from=V1EnvVarSource()),
        ],
    )
    random1 = V1Container(name="random1")
    random2 = V1Container(
        name="random2",
        env=[
            V1EnvVar(name="test", value="value"),
            V1EnvVar(name="test-from-source", value_from=V1EnvVarSource()),
        ],
    )

    new_renku_tokens = RenkuTokens(access_token="new_renku_access_token", refresh_token="new_renku_refresh_token")

    sts = V1StatefulSet(
        spec=V1StatefulSetSpec(
            service_name="test",
            selector=V1LabelSelector(),
            template=V1PodTemplateSpec(
                spec=V1PodSpec(
                    containers=[git_proxy, random1, random2], init_containers=[git_clone, random1, secrets, random2]
                )
            ),
        )
    )
    patches = NamespacedK8sClient._get_statefulset_token_patches(sts, new_renku_tokens)

    # Order of patches should be git proxy access, git proxy refresh, git clone, secrets
    assert len(patches) == 4
    # Git proxy access token
    assert patches[0]["path"] == "/spec/template/spec/containers/0/env/3/value"
    assert patches[0]["value"] == new_renku_tokens.access_token
    # Git proxy refresh token
    assert patches[1]["path"] == "/spec/template/spec/containers/0/env/2/value"
    assert patches[1]["value"] == new_renku_tokens.refresh_token
    # Git clone
    assert patches[2]["path"] == "/spec/template/spec/initContainers/0/env/1/value"
    assert patches[2]["value"] == new_renku_tokens.access_token
    # Secrets init
    assert patches[3]["path"] == "/spec/template/spec/initContainers/2/env/0/value"
    assert patches[3]["value"] == new_renku_tokens.access_token
