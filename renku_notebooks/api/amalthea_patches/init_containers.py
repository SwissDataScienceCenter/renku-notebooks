import os
from pathlib import Path
from typing import TYPE_CHECKING

from kubernetes import client

from ...config import config
from ..classes.user import RegisteredUser
from .utils import get_certificates_volume_mounts

if TYPE_CHECKING:
    from renku_notebooks.api.classes.server import UserServer


def git_clone(server: "UserServer"):
    etc_cert_volume_mount = get_certificates_volume_mounts(
        custom_certs=False,
        etc_certs=True,
        read_only_etc_certs=True,
    )
    env = [
        {"name": "GIT_CLONE_MOUNT_PATH", "value": f"/work/{server.gl_project.path}"},
        {
            "name": "GIT_CLONE_REPOSITORY_URL",
            "value": server.gl_project.http_url_to_repo,
        },
        {
            "name": "GIT_CLONE_LFS_AUTO_FETCH",
            "value": "1" if server.server_options.lfs_auto_fetch else "0",
        },
        {"name": "GIT_CLONE_COMMIT_SHA", "value": server.commit_sha},
        {"name": "GIT_CLONE_BRANCH", "value": server.branch},
        {
            # used only for naming autosave branch
            "name": "GIT_CLONE_USER__USERNAME",
            "value": server._user.username,
        },
        {
            "name": "GIT_CLONE_GIT_AUTOSAVE",
            "value": "1" if server.autosave_allowed else "0",
        },
        {"name": "GIT_CLONE_GIT_URL", "value": server._user.gitlab_client._base_url},
        {"name": "GIT_CLONE_USER__OAUTH_TOKEN", "value": server._user.git_token},
        {
            "name": "GIT_CLONE_SENTRY__ENABLED",
            "value": str(config.sessions.git_clone.sentry.enabled).lower(),
        },
        {
            "name": "GIT_CLONE_SENTRY__DSN",
            "value": config.sessions.git_clone.sentry.dsn,
        },
        {
            "name": "GIT_CLONE_SENTRY__ENVIRONMENT",
            "value": config.sessions.git_clone.sentry.env,
        },
        {
            "name": "GIT_CLONE_SENTRY__SAMPLE_RATE",
            "value": str(config.sessions.git_clone.sentry.sample_rate),
        },
        {"name": "SENTRY_RELEASE", "value": os.environ.get("SENTRY_RELEASE")},
        {
            "name": "REQUESTS_CA_BUNDLE",
            "value": str(
                Path(etc_cert_volume_mount[0]["mountPath"]) / "ca-certificates.crt"
            ),
        },
        {
            "name": "SSL_CERT_FILE",
            "value": str(
                Path(etc_cert_volume_mount[0]["mountPath"]) / "ca-certificates.crt"
            ),
        },
    ]
    if type(server._user) is RegisteredUser:
        env += [
            {"name": "GIT_CLONE_USER__EMAIL", "value": server._user.gitlab_user.email},
            {
                "name": "GIT_CLONE_USER__FULL_NAME",
                "value": server._user.gitlab_user.name,
            },
        ]
    return [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/initContainers/-",
                    "value": {
                        "image": config.sessions.git_clone.image,
                        "name": "git-clone",
                        "resources": {
                            "requests": {
                                "cpu": "100m",
                                "memory": "100Mi",
                            }
                        },
                        "securityContext": {
                            "allowPrivilegeEscalation": False,
                            "fsGroup": 100,
                            "runAsGroup": 100,
                            "runAsUser": 1000,
                            "runAsNonRoot": True,
                        },
                        "volumeMounts": [
                            {"mountPath": "/work", "name": "workspace"},
                            *etc_cert_volume_mount,
                        ],
                        "env": env,
                    },
                },
            ],
        }
    ]


def certificates():
    initContainer = client.V1Container(
        name="init-certificates",
        image=config.sessions.ca_certs.image,
        volume_mounts=get_certificates_volume_mounts(
            etc_certs=True,
            custom_certs=True,
            read_only_etc_certs=False,
        ),
        resources={
            "requests": {
                "cpu": "50m",
                "memory": "50Mi",
            }
        },
    )
    volume_etc_certs = client.V1Volume(
        name="etc-ssl-certs", empty_dir=client.V1EmptyDirVolumeSource(medium="Memory")
    )
    volume_custom_certs = client.V1Volume(
        name="custom-ca-certs",
        projected=client.V1ProjectedVolumeSource(
            default_mode=440,
            sources=[
                {"secret": {"name": i.get("secret")}}
                for i in config.sessions.ca_certs.secrets
                if i is not None and i.get("secret") is not None
            ],
        ),
    )
    api_client = client.ApiClient()
    patches = [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/initContainers/-",
                    "value": api_client.sanitize_for_serialization(initContainer),
                },
            ],
        },
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/volumes/-",
                    "value": api_client.sanitize_for_serialization(volume_etc_certs),
                },
            ],
        },
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/volumes/-",
                    "value": api_client.sanitize_for_serialization(volume_custom_certs),
                },
            ],
        },
    ]
    return patches


def download_image(server: "UserServer"):
    container = client.V1Container(
        name="download-image",
        image=server.verified_image,
        command=["sh", "-c"],
        args=["exit", "0"],
        resources={
            "requests": {
                "cpu": "50m",
                "memory": "50Mi",
            }
        },
    )
    api_client = client.ApiClient()
    return [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/initContainers/-",
                    "value": api_client.sanitize_for_serialization(container),
                },
            ],
        },
    ]
