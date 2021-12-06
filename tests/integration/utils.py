from kubernetes import client


def find_session_js(
    gitlab_project, k8s_namespace, safe_username, commit_sha, branch="master"
):
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
        js
        for js in jss["items"]
        if js["metadata"]["annotations"].get("renku.io/branch") == branch
    ]
    if len(jss) == 1:
        return jss[0]
    else:
        return None


def find_session_pod(
    gitlab_project, k8s_namespace, safe_username, commit_sha, branch="master"
):
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
