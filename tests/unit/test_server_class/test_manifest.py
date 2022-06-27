import pytest

from renku_notebooks.api.classes.server import UserServer


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
    parameters, expected, patch_user_server, user_with_project_path, app
):
    """Test that session manifest can be created correctly."""

    user = user_with_project_path("namespace/project")
    with app.app_context():
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
            },
            "branch": "master",
            "commit_sha": "abcdefg123456789",
            "notebook": "",
            "environment_variables": {},
            "cloudstorage": [],
        }

        server = UserServer(**{**base_parameters, **parameters})
        server.image_workdir = ""

        manifest = server._get_session_manifest()

    assert expected in str(manifest)
