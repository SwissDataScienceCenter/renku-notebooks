import pytest

from renku_notebooks.config import config
from tests.integration.utils import find_container, find_session_pod, is_pod_ready


@pytest.fixture(params=["commit_sha", "namespace", "project", "image"])
def invalid_payload(valid_payload, request):
    if request.param == "image":
        invalid_image = (
            config.git.registry
            + "/"
            + valid_payload["namespace"]
            + "/"
            + valid_payload["project"]
            + ":invalid"
        )
        payload = {**valid_payload, "image": invalid_image}
    else:
        payload = {**valid_payload, request.param: "invalid"}
    yield payload


@pytest.fixture(params=[None, config.sessions.default_image])
def valid_payload_image(request, valid_payload):
    image = request.param
    if image is None:
        # use image tied to the commit
        image = (
            config.git.registry
            + "/"
            + valid_payload["namespace"]
            + "/"
            + valid_payload["project"]
            + ":"
            + valid_payload["commit_sha"][:7]
        )
    else:
        # image is is pinned but valid
        valid_payload = {**valid_payload, "image": image}
    yield valid_payload, image


def test_successful_launch(
    valid_payload_image,
    gitlab_project,
    safe_username,
    k8s_namespace,
    start_session_and_wait_until_ready,
    headers,
):
    payload, image = valid_payload_image
    response = start_session_and_wait_until_ready(headers, payload, gitlab_project)
    assert response is not None and response.status_code < 300
    pod = find_session_pod(
        gitlab_project,
        k8s_namespace,
        safe_username,
        payload["commit_sha"],
        payload.get("branch", "master"),
    )
    container = find_container(pod)
    assert is_pod_ready(pod)
    assert container is not None
    assert container.image == image


def test_unsuccessful_launch(invalid_payload, launch_session, gitlab_project, headers):
    response = launch_session(headers, invalid_payload, gitlab_project)
    assert response is not None and response.status_code == 404
