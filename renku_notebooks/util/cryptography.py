"""Utility functions to get users' secret key."""

import base64
import logging

import requests
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


def get_user_key(data_svc_url: str, access_token: str) -> str | None:
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

    return get_encryption_key(user_key["secret_key"].encode(), user_id.encode()).decode("utf-8")
