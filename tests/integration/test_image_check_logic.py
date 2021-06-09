
@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_default_fallback(
    get_docker_token,
    image_exists,
    mock_requests,
    client,
    make_server_args_valid,
    kubernetes_client,
):
    payload = {**DEFAULT_PAYLOAD}
    image_exists.return_value = False
    get_docker_token.return_value = "token", False
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image")
        == os.environ["DEFAULT_IMAGE"]
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image_pull_secrets")
        is None
    )


@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_specific_found(
    get_docker_token,
    image_exists,
    mock_requests,
    client,
    make_server_args_valid,
    kubernetes_client,
):
    requested_image = "hostname.com/image/subimage:tag"
    image_exists.return_value = True
    get_docker_token.return_value = "token", False
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "commit-1", "image": requested_image}
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert image_exists.called_once_with(
        "hostname.com", "image/subimage", "tag", "token"
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image") == requested_image
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image_pull_secrets")
        is None
    )


@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_specific_not_found(
    get_docker_token, image_exists, mock_requests, client, make_server_args_valid
):
    requested_image = "hostname.com/image/subimage:tag"
    image_exists.return_value = False
    get_docker_token.return_value = None, None
    client.post(
        "/service/servers",
        headers=AUTHORIZED_HEADERS,
        json={**DEFAULT_PAYLOAD, "image": requested_image},
    )
    assert not mock_requests.post.called


@patch("renku_notebooks.api.classes.server.UserServer._create_registry_secret")
@patch("renku_notebooks.api.classes.server.requests", autospec=True)
@patch("renku_notebooks.api.classes.server.image_exists")
@patch("renku_notebooks.api.classes.server.get_docker_token")
def test_image_check_logic_commit_sha(
    get_docker_token,
    image_exists,
    mock_requests,
    create_reg_secret_mock,
    client,
    make_server_args_valid,
    kubernetes_client,
):
    payload = {**DEFAULT_PAYLOAD, "commit_sha": "5ds4af4adsf6asf4564"}
    image_exists.return_value = True
    get_docker_token.return_value = "token", True
    client.post("/service/servers", headers=AUTHORIZED_HEADERS, json=payload)
    assert create_reg_secret_mock.called_once
    assert image_exists.called_once_with(
        os.environ["IMAGE_REGISTRY"],
        payload["namespace"] + "/" + payload["project"],
        payload["commit_sha"][:7],
        "token",
    )
    assert mock_requests.post.call_args[-1].get("json", {}).get("image") == "/".join(
        [
            os.environ["IMAGE_REGISTRY"],
            payload["namespace"],
            payload["project"] + ":" + payload["commit_sha"][:7],
        ]
    )
    assert (
        mock_requests.post.call_args[-1].get("json", {}).get("image_pull_secrets")
        is not None
    )


@pytest.mark.integration
def test_public_image_check():
    parsed_image = parse_image_name("nginx:1.19.3")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parse_image_name("nginx:1.19.3"), token=token)
    parsed_image = parse_image_name("nginx")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parse_image_name("nginx"), token=token)
    parsed_image = parse_image_name("renku/singleuser:cb70d7e")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parsed_image, token=token)
    parsed_image = parse_image_name("renku/singleuser")
    token, _ = get_docker_token(**parsed_image, user={})
    assert image_exists(**parsed_image, token=token)
    parsed_image = parse_image_name("madeuprepo/madeupproject:tag")
    assert not image_exists(**parsed_image, token="madeuptoken")