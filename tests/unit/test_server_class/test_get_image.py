import pytest
from unittest.mock import MagicMock

from renku_notebooks.api.classes.server import UserServer


@pytest.fixture
def setup(mocker):
    mocker.patch("renku_notebooks.api.classes.server.UserServer._check_flask_config")
    get_k8s_client = mocker.patch("renku_notebooks.api.classes.server.get_k8s_client")
    get_k8s_client.return_value = MagicMock(), MagicMock()
    mocker.patch("renku_notebooks.api.classes.server.client")
    mocker.patch("renku_notebooks.api.classes.server.parse_image_name")


@pytest.fixture
def get_server_w_image(app, setup, user_with_project_path):
    def _get_server_w_image(image):
        user = user_with_project_path("namespace/project")
        with app.app_context():
            return UserServer(
                user,
                "namespace",
                "project",
                "branch",
                "12345678910",
                "notebook",
                image,
                "server_options",
            )

    yield _get_server_w_image


@pytest.fixture
def set_image_exists(mocker):
    def _set_image_exists(exists):
        m = mocker.patch("renku_notebooks.api.classes.server.image_exists")
        m.return_value = exists
        return m

    yield _set_image_exists


@pytest.fixture
def set_get_docker_token(mocker):
    def _set_get_docker_token(token, is_image_private):
        m = mocker.patch("renku_notebooks.api.classes.server.get_docker_token")
        m.return_value = token, is_image_private
        return m

    yield _set_get_docker_token


@pytest.fixture
def set_get_image_workdir(mocker):
    def _set_get_image_workdir(workdir):
        m = mocker.patch("renku_notebooks.api.classes.server.get_image_workdir")
        m.return_value = workdir
        return m

    yield _set_get_image_workdir


@pytest.fixture
def user_with_project_path():
    def _user_with_project_path(path):
        user = MagicMock()
        renku_project = MagicMock()
        renku_project.path_with_namespace = path
        user.get_renku_project.return_value = renku_project
        return user

    yield _user_with_project_path


@pytest.mark.parametrize("is_image_private", [True, False])
@pytest.mark.parametrize("image_name", ["image", None])
def test_valid_image(
    image_name,
    is_image_private,
    app,
    get_server_w_image,
    set_get_docker_token,
    set_image_exists,
    set_get_image_workdir,
):
    server = get_server_w_image(image_name)
    # image exists
    set_image_exists(True)
    # image is private
    set_get_docker_token("token", is_image_private)
    set_get_image_workdir("/home/workdir")
    with app.app_context():
        correct_image_name = (
            app.config["IMAGE_REGISTRY"] + "/namespace/project:1234567"
            if image_name is None  # image is not pinned
            else image_name  # image is pinned
        )
        server._verify_image()
        assert server.verified_image == correct_image_name
        assert server.is_image_private == is_image_private
        assert not server.using_default_image


@pytest.mark.parametrize("image_name", ["image", None])
def test_invalid_image(
    image_name,
    app,
    get_server_w_image,
    set_get_docker_token,
    set_image_exists,
    set_get_image_workdir,
):
    server = get_server_w_image(image_name)
    set_get_docker_token(None, None)
    set_get_image_workdir("/home/workdir")
    # image does not exists
    set_image_exists(False)
    with app.app_context():
        server._verify_image()
        if image_name is None:  # image is not pinned
            assert server.verified_image == app.config["DEFAULT_IMAGE"]
            assert not server.is_image_private
            assert server.using_default_image
        else:  # image is pinned
            assert server.verified_image is None
            assert server.is_image_private is None
            assert not server.using_default_image
