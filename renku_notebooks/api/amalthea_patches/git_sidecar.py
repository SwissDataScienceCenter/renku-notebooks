import os
from flask import current_app

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
                                "containerPort": current_app.config[
                                    "GIT_RPC_SERVER_PORT"
                                ],
                                "name": "git-port",
                                "protocol": "TCP",
                            }
                        ],
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
                                "name": "GIT_RPC_PORT",
                                "value": str(current_app.config["GIT_RPC_SERVER_PORT"]),
                            },
                            {
                                "name": "GIT_RPC_HOST",
                                "value": current_app.config["GIT_RPC_SERVER_HOST"],
                            },
                            {
                                "name": "GIT_RPC_URL_PREFIX",
                                "value": f"/sessions/{server.server_name}/sidecar/",
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
                            "httpGet": {
                                "port": current_app.config["GIT_RPC_SERVER_PORT"],
                                "path": f"/sessions/{server.server_name}/sidecar/health",
                            },
                            "periodSeconds": 10,
                            "failureThreshold": 2,
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "port": current_app.config["GIT_RPC_SERVER_PORT"],
                                "path": f"/sessions/{server.server_name}/sidecar/health",
                            },
                            "periodSeconds": 10,
                            "failureThreshold": 6,
                        },
                        "startupProbe": {
                            "httpGet": {
                                "port": current_app.config["GIT_RPC_SERVER_PORT"],
                                "path": f"/sessions/{server.server_name}/sidecar/health",
                            },
                            "periodSeconds": 10,
                            "failureThreshold": 30,
                        },
                    },
                }
            ],
        }
    ]
    # NOTE: Use the oauth2proxy is used to authenticate requests for the sidecar
    patches.append(
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "replace",
                    "path": "/statefulset/spec/template/spec/containers/1/args/6",
                    "value": f"--upstream=http://127.0.0.1:8888/sessions/{server.server_name}/",
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": (
                        f"--upstream=http://127.0.0.1:{current_app.config['GIT_RPC_SERVER_PORT']}"
                        f"/sessions/{server.server_name}/sidecar/"
                    ),
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": (
                        f"--skip-auth-route=^/sessions/{server.server_name}/sidecar/health$"
                    ),
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": (
                        f"--skip-auth-route=^/sessions/{server.server_name}/sidecar/health/$"
                    ),
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": "--skip-jwt-bearer-tokens=true",
                },
            ],
        }
    )
    return patches
