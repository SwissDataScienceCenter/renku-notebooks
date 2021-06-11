import pytest
from tests.integration.utils import find_session_pod, find_container, is_pod_ready
import os


@pytest.fixture(params=["commit_sha", "namespace", "project"])
def invalid_payload(valid_payload, request):
    payload = {**valid_payload, request.param: "invalid"}
    yield payload


@pytest.fixture(params=[None, os.environ["NOTEBOOKS_DEFAULT_IMAGE"], "invalid"])
def valid_payload_image(request, valid_payload):
    image = request.param
    if image is None:
        # use image tied to the commit
        image = (
            os.environ["GITLAB_REGISTRY"]
            + "/"
            + valid_payload["namespace"]
            + "/"
            + valid_payload["project"]
            + ":"
            + valid_payload["commit_sha"][:7]
        )
    if image == "invalid":
        # image is pinned but invalid - then use default
        invalid_image = (
            os.environ["GITLAB_REGISTRY"]
            + "/"
            + valid_payload["namespace"]
            + "/"
            + valid_payload["project"]
            + ":invalid"
        )
        image = os.environ["NOTEBOOKS_DEFAULT_IMAGE"]
        valid_payload = {**valid_payload, "image": invalid_image}
    else:
        # image is is pinned but valid
        valid_payload = {**valid_payload, "image": image}
    yield valid_payload, image


def test_successful_launch(
    valid_payload_image,
    gitlab_project,
    safe_username,
    k8s_namespace,
    launch_session,
    delete_session,
):
    payload, image = valid_payload_image
    response = launch_session(payload)
    assert response.status_code < 300
    pod = find_session_pod(
        gitlab_project, k8s_namespace, safe_username, payload["commit_sha"]
    )
    container = find_container(pod)
    assert is_pod_ready(pod)
    assert container is not None
    assert container.image == image
    session = response.json()
    delete_response = delete_session(session)
    assert delete_response is not None
    assert delete_response.status_code < 300


def test_unsuccessful_launch(invalid_payload, launch_session):
    response = launch_session(invalid_payload)
    assert response.status_code == 500
