from datetime import datetime, timedelta
from time import sleep

import pytest
import requests


@pytest.fixture
def extract_error_message(base_url, headers, default_timeout_mins):
    def _extract_error_message(server_name, timeout_mins=default_timeout_mins):
        tstart = datetime.now()
        timeout = timedelta(minutes=timeout_mins)
        # INFO: Wait to see expected error message
        while True:
            response = requests.get(
                f"{base_url}/servers/{server_name}", headers=headers
            )
            if response.status_code == 200:
                response_json = response.json()
                status_state = response_json.get("status", {}).get("state")
                if status_state == "failed":
                    error_msg = response_json.get("status", {}).get("message", "")
                    return error_msg
            if datetime.now() - tstart > timeout:
                print(
                    f"Getting the error message timed out, with response: {response.text}"
                )
                return
            sleep(10)

    yield _extract_error_message


# TODO: Find a way to enable this - currently default storage provider for kind
# does not support limit on the PVCs it provisions.
# See https://github.com/rancher/local-path-provisioner#cons
# def test_running_out_of_disk_space(
#     headers,
#     base_url,
#     valid_payload,
#     create_gitlab_project,
#     get_valid_payload,
#     extract_error_message,
#     launch_session,
# ):
#     gitlab_project = create_gitlab_project(LFS_size_megabytes=1000)
#     valid_payload = get_valid_payload(gitlab_project)
#     valid_payload = {
#         **valid_payload,
#         "serverOptions": {
#             "disk_request": "500M",
#             "lfs_auto_fetch": "true",
#         },
#     }
#     response = launch_session(headers, valid_payload, gitlab_project)
#     assert response.status_code == 201
#     session_name = response.json()["name"]
#     error_message = extract_error_message(session_name)
#     assert type(error_message) is str
#     assert "low disk space" in error_message
#     assert "restart" in error_message
#     assert "more storage" in error_message


def test_wrong_image(
    headers,
    valid_payload,
    extract_error_message,
    launch_session,
    delete_session,
    gitlab_project,
):
    valid_payload = {
        **valid_payload,
        "image": "nginx",
    }
    response = launch_session(headers, valid_payload, gitlab_project, wait_for_ci=False)
    assert response.status_code == 201
    session_name = response.json()["name"]
    error_message = extract_error_message(session_name)
    assert type(error_message) is str
    assert (
        "does not contain the required command" in error_message
        or "ensure that your Dockerfile is correct" in error_message
    )
    # NOTE: This session is crashing and will not gracefully shutdown for 10 mins
    # passing forced=True bypasses this behavious and sets the deletionGracePeriodSeconds to 0
    delete_session(response.json(), gitlab_project, headers, forced=True)
