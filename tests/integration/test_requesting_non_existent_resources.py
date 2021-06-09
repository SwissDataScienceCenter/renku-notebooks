def test_getting_logs_for_nonexisting_notebook_returns_404(client, kubernetes_client):
    response = client.get("/service/logs/non-existing-hash", headers=AUTHORIZED_HEADERS)
    assert response.status_code == 404


def test_using_extra_slashes_in_notebook_url_results_in_308(client, kubernetes_client):
    SERVER_URL_WITH_EXTRA_SLASHES = f"/{SERVER_NAME}"
    response = client.post(
        f"/service/servers/{SERVER_URL_WITH_EXTRA_SLASHES}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 308


def test_deleting_nonexisting_servers_returns_404(client, kubernetes_client):
    NON_EXISTING_SERVER_NAME = "non-existing"
    response = client.delete(
        f"/service/servers/{NON_EXISTING_SERVER_NAME}", headers=AUTHORIZED_HEADERS
    )
    assert response.status_code == 404


def test_getting_status_for_nonexisting_notebooks_returns_404(
    client, kubernetes_client
):
    headers = AUTHORIZED_HEADERS.copy()
    headers.update({"Accept": "text/plain"})
    response = client.get(f"/service/logs/{SERVER_NAME}", headers=headers)
    assert response.status_code == 404


@patch("renku_notebooks.api.classes.server.UserServer._branch_exists")
@patch("renku_notebooks.api.classes.server.UserServer._commit_sha_exists")
@patch("renku_notebooks.api.classes.server.UserServer._project_exists")
def test_project_does_not_exist(
    _project_exists,
    _commit_sha_exists,
    _branch_exists,
    client,
    make_all_images_valid,
    kubernetes_client,
):
    _project_exists.return_value = False
    _commit_sha_exists.return_value = True
    _branch_exists.return_value = True
    payload = {
        "namespace": "does_not_exist",
        "project": "does_not_exist",
        "commit_sha": "999999",
    }
    response = client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert response.status_code == 404