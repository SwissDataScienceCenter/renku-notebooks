import pytest
from unittest import mock
import os

import git_services.sidecar.rpc_server as rpc_server


@pytest.fixture
def mock_rpc_server_cli(init_git_repo):
    git_cli = init_git_repo()

    email = "test.email@sdsc.com"
    git_cli.git_config(f"--local user.email {email}")
    name = "Renku User"
    git_cli.git_config(f"--local user.name {name}")

    original_cli = rpc_server.GitCLI
    mocked_cli = mock.MagicMock(wraps=git_cli)
    mocked_cli.git_push.return_value = ""

    def _mocked_cli(path):
        return mocked_cli

    rpc_server.GitCLI = _mocked_cli
    yield mocked_cli
    rpc_server.GitCLI = original_cli


@mock.patch.dict(
    os.environ,
    {
        "MOUNT_PATH": ".",
        "CI_COMMIT_SHA": "75d22e14c12b5c70957ef73fcfdb12c03aef21bf",
        "RENKU_USERNAME": "Renku-user",
    },
    clear=True,
)
def test_autosave_clean(mock_rpc_server_cli):
    """Test no autosave branch is created on clean repo."""
    rpc_server.autosave()

    mock_rpc_server_cli.git_status.assert_called_once()
    mock_rpc_server_cli.git_commit.assert_not_called()
    mock_rpc_server_cli.git_push.assert_not_called()


@mock.patch.dict(
    os.environ,
    {
        "MOUNT_PATH": ".",
        "CI_COMMIT_SHA": "75d22e14c12b5c70957ef73fcfdb12c03aef21bf",
        "RENKU_USERNAME": "Renkuuser",
    },
    clear=True,
)
def test_autosave_unpushed_changes(mock_rpc_server_cli):
    """Test no autosave branch is created on clean repo."""
    mock_rpc_server_cli.git_status.return_value = """# branch.head master
# branch.oid 03c909db8dfdbb5ef411c086824aacd13fbad9d5
# branch.ab +1 -0"""

    rpc_server.autosave()

    mock_rpc_server_cli.git_status.assert_called_once()
    mock_rpc_server_cli.git_commit.assert_not_called()
    mock_rpc_server_cli.git_push.assert_called_once_with(
        "origin renku/autosave/Renkuuser/master/75d22e1/03c909d"
    )


@pytest.mark.parametrize(
    "status_file_line",
    [
        (
            "1 .M N... 100644 100644 100644 a85b3a6c6138a9a88f4283091130eaa1bb8853c8"
            " a85b3a6c6138a9a88f4283091130eaa1bb8853c8"
        ),
        "? ",
        (
            "1 A. N... 000000 100644 100644 0000000000000000000000000000000000000000"
            " abaf41b0f32d48161d59df7c95b40afe5d5227f8 "
        ),
        (
            "2 R. N... 100644 100644 100644 abaf41b0f32d48161d59df7c95b40afe5d5227f8"
            " abaf41b0f32d48161d59df7c95b40afe5d5227f8 R100"
        ),
    ],
)
@mock.patch.dict(
    os.environ,
    {
        "MOUNT_PATH": ".",
        "CI_COMMIT_SHA": "75d22e14c12b5c70957ef73fcfdb12c03aef21bf",
        "RENKU_USERNAME": "Renku-user",
    },
    clear=True,
)
def test_autosave_dirty_changes(status_file_line, mock_rpc_server_cli):
    """Test no autosave branch is created on clean repo."""
    mock_rpc_server_cli.git_status.return_value = f"""# branch.head master
# branch.oid 03c909db8dfdbb5ef411c086824aacd13fbad9d5
# branch.ab +0 -0
{status_file_line} my_file"""

    rpc_server.autosave()

    mock_rpc_server_cli.git_status.assert_called_once()
    mock_rpc_server_cli.git_commit.assert_called_once_with(
        "--no-verify -m 'Auto-saving for Renku-user on branch master from commit 75d22e1'"
    )
    mock_rpc_server_cli.git_push.assert_called_once_with(
        "origin renku/autosave/Renku-user/master/75d22e1/03c909d"
    )