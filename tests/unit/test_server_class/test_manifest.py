from pathlib import Path
from typing import Any

import pytest

from renku_notebooks.api.classes.k8s_client import K8sClient
from renku_notebooks.api.classes.server import UserServer
from renku_notebooks.api.schemas.secrets import K8sUserSecrets
from renku_notebooks.api.schemas.server_options import ServerOptions
from renku_notebooks.errors.programming import DuplicateEnvironmentVariableError
from renku_notebooks.errors.user import OverriddenEnvironmentVariableError

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
    "user_secrets": None,
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

        server = UserServer(**{**base_parameters, **parameters})
        server._repositories = {}

        manifest = server._get_session_manifest()

    assert expected in str(manifest)


@pytest.fixture()
def reference_secrets_patch():
    return [
        {
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/initContainers/-",
                    "value": {
                        "env": [
                            {
                                "name": "DATA_SERVICE_URL",
                                "value": "http://renku-data-service",
                            },
                            {
                                "name": "RENKU_ACCESS_TOKEN",
                                "value": "REPLACE_WITH_MOCK",
                            },
                            {
                                "name": "ENCRYPTED_SECRETS_MOUNT_PATH",
                                "value": "/encrypted",
                            },
                            {
                                "name": "DECRYPTED_SECRETS_MOUNT_PATH",
                                "value": "/decrypted",
                            },
                        ],
                        "image": "renku/secrets-mount:latest",
                        "name": "init-user-secrets",
                        "resources": {"requests": {"cpu": "50m", "memory": "50Mi"}},
                        "volumeMounts": [
                            {
                                "mountPath": "/encrypted",
                                "name": "test_secret-volume",
                                "readOnly": True,
                            },
                            {
                                "mountPath": "/decrypted",
                                "name": "user-secrets-volume",
                                "readOnly": False,
                            },
                        ],
                    },
                }
            ],
            "type": "application/json-patch+json",
        },
        {
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/volumes/-",
                    "value": {
                        "emptyDir": {"medium": "Memory"},
                        "name": "user-secrets-volume",
                    },
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/volumes/-",
                    "value": {
                        "name": "test_secret-volume",
                        "secret": {"secretName": "test_secret"},
                    },
                },
            ],
            "type": "application/json-patch+json",
        },
        {
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/0/volumeMounts/-",
                    "value": {
                        "mountPath": "/run/secrets",
                        "name": "user-secrets-volume",
                        "readOnly": True,
                    },
                }
            ],
            "type": "application/json-patch+json",
        },
    ]


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {
            "user_secrets": K8sUserSecrets(
                name="test_secret",
                user_secret_ids=["TEST1", "TEST2"],
                mount_path="/run/secrets",
            )
        },
    ],
    ids=["Without secrets", "With secrets"],
)
def test_user_secrets_manifest(
    parameters,
    reference_secrets_patch,
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

        server = UserServer(**{**base_parameters, **parameters})
        server._repositories = {}

        manifest = server._get_session_manifest()

    reference_secrets_patch[0]["patch"][0]["value"]["env"][1]["value"] = str(base_parameters["user"].access_token)

    for expected_item in reference_secrets_patch:
        if parameters:
            assert expected_item in manifest["spec"]["patches"]
        else:
            assert expected_item not in manifest["spec"]["patches"]


def test_session_env_var_override(patch_user_server, user_with_project_path, app, mocker):
    """Test that when a patch overrides session env vars an error is raised."""
    with app.app_context():
        parameters: dict[str, Any] = BASE_PARAMETERS.copy()
        parameters["user"] = user_with_project_path("namespace/project")
        parameters["k8s_client"] = mocker.MagicMock(K8sClient)
        # NOTE: NOTEBOOK_DIR is defined in ``jupyter_server.env`` patch
        parameters["environment_variables"] = {"NOTEBOOK_DIR": "/some/path"}

        server = UserServer(**parameters)
        server._repositories = {}

        with pytest.raises(OverriddenEnvironmentVariableError):
            server._get_session_manifest()


def test_patches_env_var_override(patch_user_server, user_with_project_path, app, mocker):
    """Test that when multiple patches define the same env vars with different values an error is
    raised.
    """
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

        server = UserServer(**parameters)
        server._repositories = {}

        with pytest.raises(DuplicateEnvironmentVariableError):
            server._get_session_manifest()
