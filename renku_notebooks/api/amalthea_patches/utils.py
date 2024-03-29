from kubernetes import client

from ...config import config


def get_certificates_volume_mounts(
    etc_certs: bool = True,
    custom_certs: bool = True,
    read_only_etc_certs: bool = False,
):
    volume_mounts = []
    etc_ssl_certs = client.V1VolumeMount(
        name="etc-ssl-certs",
        mount_path="/etc/ssl/certs/",
        read_only=read_only_etc_certs,
    )
    custom_ca_certs = client.V1VolumeMount(
        name="custom-ca-certs",
        mount_path=config.sessions.ca_certs.path,
        read_only=True,
    )
    if etc_certs:
        volume_mounts.append(etc_ssl_certs)
    if custom_certs:
        volume_mounts.append(custom_ca_certs)
    return client.ApiClient().sanitize_for_serialization(volume_mounts)
