import shutil

import pytest
import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes import watch


@pytest.mark.skipif(shutil.which("k3d") is None, reason="Requires k3d for cluster creation")
def test_with_user_secrets(cluster, client, fake_gitlab, proper_headers, user_with_project_path, mock_data_svc):
    project_namespace = "test-namespace"
    project_name = "my-test"
    project_path = f"{project_namespace}/{project_name}"
    user = user_with_project_path(project_path)

    k8s_config.load_kube_config_from_dict(yaml.safe_load(cluster.config_yaml()))
    core_api = k8s_client.CoreV1Api()
    node_list = core_api.list_node()
    assert len(node_list.items) == 2, "Unable to get running nodes from k3s cluster"

    co_api = k8s_client.CustomObjectsApi()

    amalthea_helmchart = {
        "group": "helm.cattle.io",
        "version": "v1",
        "namespace": "kube-system",
        "plural": "helmcharts",
        "body": {
            "apiVersion": "helm.cattle.io/v1",
            "kind": "HelmChart",
            "metadata": {
                "name": "amalthea",
            },
            "spec": {
                "repo": "https://swissdatasciencecenter.github.io/helm-charts",
                "chart": "amalthea",
                "targetNamespace": "renku",
                "createNamespace": True,
            },
        },
    }

    try:
        co_api.create_namespaced_custom_object(**amalthea_helmchart)
    except k8s_client.rest.ApiException as e:
        print(f"Exception when calling CustomObjectsApi->create_namespaced_custom_object: {e}\n")
        raise

    watcher = watch.Watch()

    for event in watcher.stream(
        core_api.list_namespaced_pod,
        label_selector="app.kubernetes.io/name=amalthea",
        namespace="renku",
        timeout_seconds=60,
    ):
        if event["object"].status.phase == "Running":
            watcher.stop()
            break
    else:
        assert False, "Timeout waiting on amalthea to run"

    from renku_notebooks.util.kubernetes_ import make_server_name

    secret_data = {"01234567890123456789012345": "secret_encrypted_data"}
    branch = "main"
    commit_sha = "ee4b1c9fedc99abe5892ee95320bbd8471c5985b"
    server_name = make_server_name(user.safe_username, project_namespace, project_name, branch, commit_sha)
    secret_name = f"{server_name}-secret"
    secret = k8s_client.V1Secret(metadata=k8s_client.V1ObjectMeta(name=secret_name), string_data=secret_data)

    core_api.create_namespaced_secret(namespace="renku", body=secret)

    response = client.post(
        "/notebooks/servers",
        headers=proper_headers,
        json={
            "user_secrets": {
                "mount_path": "/bin/test/",
                "user_secret_ids": ["01234567890123456789012345"],
            },
            "project": project_name,
            "branch": "main",
            "namespace": project_namespace,
            "commit_sha": commit_sha,
            "image": "debian/bookworm",  # otherwise tries to grab it from Gitlab
        },
    )

    assert response.status_code == 201, response.json

    response = client.post(
        "/notebooks/servers",
        headers=proper_headers,
        json={
            "user_secrets": {
                "mount_path": "/test",
                "user_secret_ids": ["01234567890123456789012345"],
            },
            "project": project_name,
            "branch": "main",
            "namespace": project_namespace,
            "commit_sha": commit_sha,
            "image": "debian/bookworm",  # otherwise tries to grab it from Gitlab
        },
    )

    assert response.status_code == 201, response.json

    apps_api = k8s_client.AppsV1Api()

    stateful_set = None
    for event in watcher.stream(
        apps_api.list_namespaced_stateful_set,
        label_selector=f"amalthea.dev/parent-name={server_name}",
        namespace="renku",
        timeout_seconds=60 * 5,
    ):
        if event["type"].lower() == "added":
            stateful_set = event["object"]
            watcher.stop()
            break
        else:
            print(event["type"])
    else:
        assert False, "Timeout waiting on StatefulSet creation"

    pod_spec = stateful_set.spec.template.spec
    assert "init-user-secrets" in [container.name for container in pod_spec.init_containers]

    default_container = pod_spec.containers[0]
    assert "user-secrets-volume" in [volume_mount.name for volume_mount in default_container.volume_mounts]
    assert "user-secrets-volume" in [volume.name for volume in pod_spec.volumes]
