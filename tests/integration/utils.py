from datetime import datetime, timedelta
from time import sleep

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.client.models import V1DeleteOptions


def find_session_js(gitlab_project, k8s_namespace, safe_username, commit_sha, branch="master"):
    k8s_client = client.CustomObjectsApi(client.ApiClient())
    label_selector = ",".join(
        [
            "component=singleuser-server",
            f"renku.io/gitlabProjectId={gitlab_project.id}",
            f"renku.io/safe-username={safe_username}",
            f"renku.io/commit-sha={commit_sha}",
        ]
    )
    jss = k8s_client.list_namespaced_custom_object(
        group="amalthea.dev",
        version="v1alpha1",
        namespace=k8s_namespace,
        plural="jupyterservers",
        label_selector=label_selector,
    )
    jss = [
        js for js in jss["items"] if js["metadata"]["annotations"].get("renku.io/branch") == branch
    ]
    if len(jss) == 1:
        return jss[0]
    else:
        return None


def find_session_pod(gitlab_project, k8s_namespace, safe_username, commit_sha, branch="master"):
    js = find_session_js(gitlab_project, k8s_namespace, safe_username, commit_sha, branch)
    if js is None:
        return None
    else:
        app_name = js["metadata"]["name"]
    v1 = client.CoreV1Api()
    label_selector = ",".join(
        [
            "component=singleuser-server",
            f"renku.io/gitlabProjectId={gitlab_project.id}",
            f"renku.io/safe-username={safe_username}",
            f"renku.io/commit-sha={commit_sha}",
            f"app={app_name}",
        ]
    )
    pods = v1.list_namespaced_pod(k8s_namespace, label_selector=label_selector)
    if len(pods.items) == 1:
        return pods.items[0]
    else:
        return None


def find_container(pod):
    for container in pod.spec.containers:
        if container.name == "jupyter-server":
            return container
    return None


def is_pod_ready(pod):
    if pod is None:
        return False
    container_statuses = pod.status.container_statuses
    return (
        container_statuses is not None
        and len(container_statuses) > 0
        and all([cs.ready for cs in container_statuses])
        and pod.metadata.deletion_timestamp is None
    )


def delete_session_js(name, k8s_namespace):
    k8s_client = client.CustomObjectsApi(client.ApiClient())
    try:
        k8s_client.delete_namespaced_custom_object(
            group="amalthea.dev",
            version="v1alpha1",
            namespace=k8s_namespace,
            plural="jupyterservers",
            name=name,
            body=V1DeleteOptions(propagation_policy="Foreground"),
        )
    except ApiException as err:
        if err.status == 404:
            # INFO: The resource is already gone
            return True
        else:
            raise
    else:
        # INFO: Wait for session to be fully deleted
        tstart = datetime.now()
        timeout = timedelta(minutes=5)
        while True:
            try:
                k8s_client.get_namespaced_custom_object(
                    group="amalthea.dev",
                    version="v1alpha1",
                    namespace=k8s_namespace,
                    plural="jupyterservers",
                    name=name,
                )
            except ApiException as err:
                if err.status == 404:
                    return True
                else:
                    raise
            if datetime.now() - tstart > timeout:
                return False
            else:
                sleep(10)
