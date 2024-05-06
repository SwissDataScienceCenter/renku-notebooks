"""Test secret decryption."""

import base64
import secrets

import pytest
import responses
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from secrets_mount.__main__ import main


def _get_encryption_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password))


def _encrypt_string(password: bytes, salt: str, data: str) -> bytes:
    """Encrypt a given string."""
    key = _get_encryption_key(password=password, salt=salt.encode())
    return Fernet(key).encrypt(data.encode())


@pytest.fixture
def secret_key():
    """Create a dummy user secret key."""
    secret_key = secrets.token_hex(32)
    yield secret_key


@pytest.fixture
def setup_secret(tmp_path, monkeypatch):
    """Setup secrets folders."""
    secrets_folder = tmp_path / "secrets_enc"
    secrets_folder.mkdir()
    secrets_target_folder = tmp_path / "secrets"
    secrets_target_folder.mkdir()
    monkeypatch.setenv("ENCRYPTED_SECRETS_MOUNT_PATH", str(secrets_folder))
    monkeypatch.setenv("DECRYPTED_SECRETS_MOUNT_PATH", str(secrets_target_folder))
    yield secrets_folder, secrets_target_folder


@pytest.fixture
def create_secrets(secret_key, setup_secret):
    """Create some secrets on disk."""
    secrets_folder, secrets_target_folder = setup_secret

    secret1 = "mysecret1"

    with (secrets_folder / "secret1").open("w") as f:
        f.write(_encrypt_string(secret_key.encode(), "user", secret1).decode())

    secret2 = "mysecret2"

    with (secrets_folder / "secret2").open("w") as f:
        f.write(_encrypt_string(secret_key.encode(), "user", secret2).decode())

    yield secret1, secret2


@pytest.fixture
def mock_data_svc(secret_key, monkeypatch):
    """Mock data services."""
    data_svc_url = "http://data-service/api/data"
    monkeypatch.setenv("RENKU_ACCESS_TOKEN", "abcdefg")
    monkeypatch.setenv("DATA_SERVICE_URL", data_svc_url)
    with responses.RequestsMock() as rsps:
        rsps.get(f"{data_svc_url}/user", json={"id": "user"}, status=200)
        rsps.get(f"{data_svc_url}/user/secret_key", json=secret_key, status=200)

        yield


def test_decryption(setup_secret, create_secrets, mock_data_svc):
    """Test that mounted secrets can be decrypted."""
    _, secrets_target_folder = setup_secret
    secret1_value, secret2_value = create_secrets
    main()

    secret1 = secrets_target_folder / "secret1"
    assert secret1.read_text() == secret1_value

    secret2 = secrets_target_folder / "secret2"
    assert secret2.read_text() == secret2_value

    assert len(list(secrets_target_folder.iterdir())) == 2


def test_decryption_no_secrets(setup_secret, mock_data_svc):
    """Test that the init job passes when there's no secrets mounted."""
    _, secrets_target_folder = setup_secret
    main()

    assert len(list(secrets_target_folder.iterdir())) == 0
