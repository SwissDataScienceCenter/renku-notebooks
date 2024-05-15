from pathlib import Path
from typing import Any, Dict

import pytest

from renku_notebooks.api.classes.k8s_client import K8sClient
from renku_notebooks.api.classes.server import UserServer
from renku_notebooks.api.schemas.server_options import ServerOptions
from renku_notebooks.errors.programming import DuplicateEnvironmentVariableError
from renku_notebooks.errors.user import OverriddenEnvironmentVariableError
from renku_notebooks.util.kubernetes_ import renku_1_make_server_name

BASE_PARAMETERS = {
    "namespace": "test-namespace",
    "project": "test-project",
    "image": None,
    "server_options": ServerOptions(
        lfs_auto_fetch=0,
        default_url="/lab",
        cpu=100,
        memory=100,
        storage=100,
        gpu=0,
    ),
    "branch": "master",
    "commit_sha": "abcdefg123456789",
    "notebook": "",
    "environment_variables": {},
    "cloudstorage": [],
    "workspace_mount_path": Path("/workspace"),
    "work_dir": Path("/workspace/work/test-namespace/test-project"),
}


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
    with app.app_context():
        base_parameters = BASE_PARAMETERS.copy()
        base_parameters["user"] = user_with_project_path("namespace/project")
        base_parameters["k8s_client"] = mocker.MagicMock(K8sClient)
        base_parameters["server_name"] = renku_1_make_server_name(
            safe_username=base_parameters["user"].safe_username,
            namespace=base_parameters["namespace"],
            project=base_parameters["project"],
            branch=base_parameters["branch"],
            commit_sha=base_parameters["commit_sha"],
        )

        server = UserServer(**{**base_parameters, **parameters})
        server._repositories = {}

        manifest = server._get_session_manifest()

    assert expected in str(manifest)


def test_session_env_var_override(patch_user_server, user_with_project_path, app, mocker):
    """Test that when a patch overrides session env vars an error is raised."""
    with app.app_context():
        parameters: Dict[str, Any] = BASE_PARAMETERS.copy()
        parameters["user"] = user_with_project_path("namespace/project")
        parameters["k8s_client"] = mocker.MagicMock(K8sClient)
        # NOTE: NOTEBOOK_DIR is defined in ``jupyter_server.env`` patch
        parameters["environment_variables"] = {"NOTEBOOK_DIR": "/some/path"}
        parameters["server_name"] = renku_1_make_server_name(
            safe_username=parameters["user"].safe_username,
            namespace=parameters["namespace"],
            project=parameters["project"],
            branch=parameters["branch"],
            commit_sha=parameters["commit_sha"],
        )

        server = UserServer(**parameters)
        server._repositories = {}

        with pytest.raises(OverriddenEnvironmentVariableError):
            server._get_session_manifest()


def test_patches_env_var_override(patch_user_server, user_with_project_path, app, mocker):
    """Test that when multiple patches define the same env vars with different values an error is
    raised."""
    general_patches = mocker.patch(
        "renku_notebooks.api.classes.server.general_patches.oidc_unverified_email",
        autospec=True,
    )
    # NOTE: Override ``jupyter_server.env::RENKU_USERNAME`` env var with a different value
    general_patches.return_value = [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/0/env/-",
                    "value": {
                        "name": "RENKU_USERNAME",
                        "value": "some-different-value",
                    },
                },
            ],
        }
    ]

    with app.app_context():
        parameters = BASE_PARAMETERS.copy()
        parameters["user"] = user_with_project_path("namespace/project")
        parameters["k8s_client"] = mocker.MagicMock(K8sClient)
        parameters["server_name"] = renku_1_make_server_name(
            safe_username=parameters["user"].safe_username,
            namespace=parameters["namespace"],
            project=parameters["project"],
            branch=parameters["branch"],
            commit_sha=parameters["commit_sha"],
        )

        server = UserServer(**parameters)
        server._repositories = {}

        with pytest.raises(DuplicateEnvironmentVariableError):
            server._get_session_manifest()
