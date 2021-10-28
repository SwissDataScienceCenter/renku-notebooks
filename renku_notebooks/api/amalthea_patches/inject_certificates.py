from pathlib import Path

from .utils import get_certificates_volume_mounts


def oauth2_proxy():
    etc_cert_volume_mounts = get_certificates_volume_mounts(
        custom_certs=False,
        etc_certs=True,
        read_only_etc_certs=True,
    )
    patches = [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": (
                        "/statefulset/spec/template" "/spec/containers/1/volumeMounts/-"
                    ),
                    "value": volume_mount,
                }
                for volume_mount in etc_cert_volume_mounts
            ],
        },
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/env/-",
                    "value": {
                        "name": "OAUTH2_PROXY_PROVIDER_CA_FILES",
                        "value": ",".join(
                            [
                                (
                                    Path(volume_mount["mountPath"])
                                    / "ca-certificates.crt"
                                ).as_posix()
                                for volume_mount in etc_cert_volume_mounts
                            ]
                        ),
                    },
                },
            ],
        },
    ]
    return patches
