import pytest

from renku_notebooks.api.classes.k8s_client import K8sClient
from renku_notebooks.api.classes.server import UserServer
from renku_notebooks.errors.user import OverriddenEnvironmentVariableError


# TODO: Add more tests https://github.com/SwissDataScienceCenter/renku-notebooks/issues/1145
@pytest.mark.parametrize(
    "parameters,expected",
    [
        (
            {"environment_variables": {"TEST": "testval"}},
            "/containers/0/env/-', 'value': {'name': 'TEST', 'value': 'testval'}",
        )
    ],
)
def test_session_manifest(
    parameters,
    expected,
    patch_user_server,
    user_with_project_path,
    app,
    mocker,
):
    """Test that session manifest can be created correctly."""

    user = user_with_project_path("namespace/project")
    with app.app_context():
        mock_k8s_client = mocker.MagicMock(K8sClient)
        base_parameters = {
            "user": user,
            "namespace": "test-namespace",
            "project": "test-project",
            "image": None,
            "server_options": {
                "lfs_auto_fetch": 0,
                "defaultUrl": "/lab",
                "cpu_request": "100",
                "mem_request": "100",
                "disk_request": "100",
            },
            "branch": "master",
            "commit_sha": "abcdefg123456789",
            "notebook": "",
            "environment_variables": {},
            "cloudstorage": [],
            "k8s_client": mock_k8s_client,
        }

        server = UserServer(**{**base_parameters, **parameters})
        server.image_workdir = ""

        manifest = server._get_session_manifest()

    assert expected in str(manifest)


def test_session_env_var_override(
    patch_user_server, user_with_project_path, app, mocker
):
    """Test that when a patch overrides session env vars an error is raised."""

    user = user_with_project_path("namespace/project")
    with app.app_context():
        mock_k8s_client = mocker.MagicMock(K8sClient)
        parameters = {
            "user": user,
            "namespace": "test-namespace",
            "project": "test-project",
            "image": None,
            "server_options": {
                "lfs_auto_fetch": 0,
                "defaultUrl": "/lab",
                "cpu_request": "100",
                "mem_request": "100",
                "disk_request": "100",
            },
            "branch": "master",
            "commit_sha": "abcdefg123456789",
            "notebook": "",
            # NOTE: NOTEBOOK_DIR is defined in ``jupyter_server.env`` patch
            "environment_variables": {"NOTEBOOK_DIR": "/some/path"},
            "cloudstorage": [],
            "k8s_client": mock_k8s_client,
        }

        server = UserServer(**parameters)
        server.image_workdir = ""

        with pytest.raises(OverriddenEnvironmentVariableError) as e:
            server._get_session_manifest()
