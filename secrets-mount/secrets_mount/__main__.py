"""Sidecar code for decrypting and mounting secrets."""

import base64
import logging
import os
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def get_encryption_key(password: bytes, salt: bytes) -> bytes:
    """Derive an encryption key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password))


def decrypt_string(key: bytes, data: bytes) -> str:
    """Decrypt a given string."""
    return Fernet(key).decrypt(data).decode()


def decrypt_secret(file: Path, target: Path, key: bytes):
    """Decrypt a users secret."""
    logging.info(f"Decrypting {file}")
    with file.open() as f:
        content = f.read()

    decrypted = decrypt_string(key, content.encode())

    with (target / file.name).open("w") as f:
        f.write(decrypted)


def get_user_key(data_svc_url: str, access_token: str) -> bytes | None:
    """Get the users decryption key."""

    response = requests.get(f"{data_svc_url}/user", headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code != 200:
        logging.error(f"Couldn't get user info: {response.json()}")
        return

    user_info = response.json()
    user_id = user_info["id"]

    response = requests.get(
        f"{data_svc_url}/user/secret_key",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        logging.error(f"Couldn't get user key: {response.json()}")
        return
    user_key = response.json()

    return get_encryption_key(user_key["secret_key"].encode(), user_id.encode())


def main():
    """Decrypt user secrets to target directory."""
    logging.basicConfig(level=logging.INFO)

    user_token = os.environ.get("RENKU_ACCESS_TOKEN")
    if user_token is None:
        logging.warn("No user token set, skipping secrets mount")
        return

    data_svc_url = os.environ.get("DATA_SERVICE_URL")
    if data_svc_url is None:
        logging.error("DATA_SERVICE_URL not set")
        return

    encrypted_secrets_mount_path = Path(os.environ.get("ENCRYPTED_SECRETS_MOUNT_PATH", "/secrets_enc/"))
    if not encrypted_secrets_mount_path.exists():
        logging.info("no encrypted secrets mounted on session, skipping secrets mount")
        return
    decrypted_secrets_mount_path = Path(os.environ.get("DECRYPTED_SECRETS_MOUNT_PATH", "/secrets/"))
    if not decrypted_secrets_mount_path.exists():
        logging.error("Mount path for decrypted secrets does not exist.")
        return

    logging.info("Getting users secret key")
    user_key = get_user_key(data_svc_url, user_token)
    if user_key is None:
        return

    logging.info("Decrypting user secrets")

    for entry in encrypted_secrets_mount_path.iterdir():
        if entry.is_dir():
            continue

        decrypt_secret(entry, decrypted_secrets_mount_path, user_key)


main()
