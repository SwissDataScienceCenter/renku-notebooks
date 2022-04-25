import os
from flask import current_app
import base64
import secrets

from ..classes.user import RegisteredUser


def main(server):
    # NOTE: Autosaves can be created only for registered users
    lifecycle = (
        {
            "preStop": {
                "exec": {
                    "command": [
                        "poetry",
                        "run",
                        "python",
                        "-m",
                        "git_services.sidecar.run_command",
                        "autosave",
                    ]
                }
            }
        }
        if type(server._user) is RegisteredUser
        else {}
    )
    patches = [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/-",
                    "value": {
                        "image": current_app.config["GIT_RPC_SERVER_IMAGE"],
                        "name": "git-sidecar",
                        "ports": [
                            {
                                "containerPort": 4000,
                                "name": "git-port",
                                "protocol": "TCP",
                            }
                        ],
                        "workingDir": server.image_workdir.rstrip("/")
                        + f"/work/{server.gl_project.path}/",
                        "resources": {
                            "requests": {"memory": "32Mi", "cpu": "50m"},
                            "limits": {"memory": "64Mi", "cpu": "100m"},
                        },
                        "env": [
                            {
                                "name": "MOUNT_PATH",
                                "value": f"/work/{server.gl_project.path}",
                            },
                            {
                                "name": "GIT_RPC_SENTRY__ENABLED",
                                "value": os.environ.get("SIDECAR_SENTRY_ENABLED"),
                            },
                            {
                                "name": "GIT_RPC_SENTRY__DSN",
                                "value": os.environ.get("SIDECAR_SENTRY_DSN"),
                            },
                            {
                                "name": "GIT_RPC_SENTRY__ENVIRONMENT",
                                "value": os.environ.get("SIDECAR_SENTRY_ENV"),
                            },
                            {
                                "name": "GIT_RPC_SENTRY__SAMPLE_RATE",
                                "value": os.environ.get("SIDECAR_SENTRY_SAMPLE_RATE"),
                            },
                            {
                                "name": "SENTRY_RELEASE",
                                "value": os.environ.get("SENTRY_RELEASE"),
                            },
                            {
                                "name": "CI_COMMIT_SHA",
                                "value": f"{server.commit_sha}",
                            },
                            {
                                "name": "RENKU_USERNAME",
                                "value": f"{server._user.username}",
                            },
                            # NOTE: The git proxy health port is also used to signal that the proxy
                            # can safely shut down after any autosave branches have been properly
                            # created.
                            {
                                "name": "GIT_PROXY_HEALTH_PORT",
                                "value": current_app.config["GIT_PROXY_HEALTH_PORT"],
                            },
                            {
                                "name": "AUTOSAVE_MINIMUM_LFS_FILE_SIZE_BYTES",
                                "value": str(
                                    current_app.config[
                                        "AUTOSAVE_MINIMUM_LFS_FILE_SIZE_BYTES"
                                    ]
                                ),
                            },
                            {
                                "name": "RPC_SERVER_AUTH_TOKEN",
                                "valueFrom": {
                                    "secretKeyRef": {
                                        "name": server.server_name,
                                        "key": "rpcServerAuthToken",
                                    },
                                },
                            },
                        ],
                        # NOTE: Autosave Branch creation
                        "lifecycle": lifecycle,
                        "securityContext": {
                            "allowPrivilegeEscalation": False,
                            "fsGroup": 100,
                            "runAsGroup": 1000,
                            "runAsUser": 1000,
                            "runAsNonRoot": True,
                        },
                        "volumeMounts": [
                            {
                                "mountPath": f"/work/{server.gl_project.path}/",
                                "name": "workspace",
                                "subPath": f"{server.gl_project.path}/",
                            }
                        ],
                        "livenessProbe": {
                            "httpGet": {"port": 4000, "path": "/"},
                            "periodSeconds": 10,
                            "failureThreshold": 2,
                        },
                        "readinessProbe": {
                            "httpGet": {"port": 4000, "path": "/"},
                            "periodSeconds": 10,
                            "failureThreshold": 6,
                        },
                        "startupProbe": {
                            "httpGet": {"port": 4000, "path": "/"},
                            "periodSeconds": 10,
                            "failureThreshold": 30,
                        },
                    },
                }
            ],
        }
    ]
    # INFO: Add token (i.e. API key) for the rpc server
    patches.append(
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/secret/data/rpcServerAuthToken",
                    "value": base64.urlsafe_b64encode(
                        secrets.token_urlsafe(32).encode()
                    ).decode(),
                }
            ],
        }
    )
    # INFO: Expose the git sidecar service.
    patches.append(
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/service/spec/ports/-",
                    "value": {
                        "name": "git-rpc-server-port",
                        "port": 4000,
                        "protocol": "TCP",
                        "targetPort": 4000,
                    },
                }
            ],
        }
    )
    return patches
