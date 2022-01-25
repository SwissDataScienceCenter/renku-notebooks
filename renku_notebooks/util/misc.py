import json
import os
from flask import current_app
from kubernetes import client


def read_server_options_ui():
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_UI_PATH",
        "/etc/renku-notebooks/server_options/server_options.json",
    )
    if os.getenv("TELEPRESENCE_ROOT") is not None:
        server_options_file = os.path.join(
            os.getenv("TELEPRESENCE_ROOT"),
            server_options_file.lstrip("/"),
        )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options


def read_server_options_defaults():
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH",
        "/etc/renku-notebooks/server_options/server_defaults.json",
    )
    if os.getenv("TELEPRESENCE_ROOT") is not None:
        server_options_file = os.path.join(
            os.getenv("TELEPRESENCE_ROOT"),
            server_options_file.lstrip("/"),
        )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options


def get_certificates_volume_mounts(
    etc_certs=True,
    custom_certs=True,
    read_only_etc_certs=False,
):
    volume_mounts = []
    etc_ssl_certs = client.V1VolumeMount(
        name="etc-ssl-certs",
        mount_path="/etc/ssl/certs/",
        read_only=read_only_etc_certs,
    )
    custom_ca_certs = client.V1VolumeMount(
        name="custom-ca-certs",
        mount_path=current_app.config["CUSTOM_CA_CERTS_PATH"],
        read_only=True,
    )
    if etc_certs:
        volume_mounts.append(etc_ssl_certs)
    if custom_certs:
        volume_mounts.append(custom_ca_certs)
    return client.ApiClient().sanitize_for_serialization(volume_mounts)
