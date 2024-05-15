import os
from typing import TYPE_CHECKING

from renku_notebooks.api.classes.user import RegisteredUser
from renku_notebooks.config import config

if TYPE_CHECKING:
    from renku_notebooks.api.classes.server import UserServer


def main(server: "UserServer"):
    # NOTE: Sessions can be persisted only for registered users
    if not isinstance(server.user, RegisteredUser):
        return []

    gl_project_path = server.gitlab_project.path if hasattr(server, "gitlab_project") else "."
    commit_sha = getattr(server, "commit_sha", None)

    patches = [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/-",
                    "value": {
                        "image": config.sessions.git_rpc_server.image,
                        "name": "git-sidecar",
                        "ports": [
                            {
                                "containerPort": config.sessions.git_rpc_server.port,
                                "name": "git-port",
                                "protocol": "TCP",
                            }
                        ],
                        "resources": {
                            "requests": {"memory": "84Mi", "cpu": "100m"},
                        },
                        "env": [
                            {
                                "name": "GIT_RPC_MOUNT_PATH",
                                "value": f"/work/{gl_project_path}",
                            },
                            {
                                "name": "GIT_RPC_PORT",
                                "value": str(config.sessions.git_rpc_server.port),
                            },
                            {
                                "name": "GIT_RPC_HOST",
                                "value": config.sessions.git_rpc_server.host,
                            },
                            {
                                "name": "GIT_RPC_URL_PREFIX",
                                "value": f"/sessions/{server.server_name}/sidecar/",
                            },
                            {
                                "name": "GIT_RPC_SENTRY__ENABLED",
                                "value": str(config.sessions.git_rpc_server.sentry.enabled).lower(),
                            },
                            {
                                "name": "GIT_RPC_SENTRY__DSN",
                                "value": config.sessions.git_rpc_server.sentry.dsn,
                            },
                            {
                                "name": "GIT_RPC_SENTRY__ENVIRONMENT",
                                "value": config.sessions.git_rpc_server.sentry.env,
                            },
                            {
                                "name": "GIT_RPC_SENTRY__SAMPLE_RATE",
                                "value": str(config.sessions.git_rpc_server.sentry.sample_rate),
                            },
                            {
                                "name": "SENTRY_RELEASE",
                                "value": os.environ.get("SENTRY_RELEASE"),
                            },
                            {
                                "name": "CI_COMMIT_SHA",
                                "value": f"{commit_sha}",
                            },
                            {
                                "name": "RENKU_USERNAME",
                                "value": f"{server.user.username}",
                            },
                            {
                                "name": "GIT_RPC_GIT_PROXY_HEALTH_PORT",
                                "value": str(config.sessions.git_proxy.health_port),
                            },
                        ],
                        "securityContext": {
                            "allowPrivilegeEscalation": False,
                            "fsGroup": 100,
                            "runAsGroup": 1000,
                            "runAsUser": 1000,
                            "runAsNonRoot": True,
                        },
                        "volumeMounts": [
                            {
                                "mountPath": f"/work/{gl_project_path}/",
                                "name": "workspace",
                                "subPath": f"{gl_project_path}",
                            }
                        ],
                        "livenessProbe": {
                            "httpGet": {
                                "port": config.sessions.git_rpc_server.port,
                                "path": f"/sessions/{server.server_name}/sidecar/health",
                            },
                            "periodSeconds": 10,
                            "failureThreshold": 2,
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "port": config.sessions.git_rpc_server.port,
                                "path": f"/sessions/{server.server_name}/sidecar/health",
                            },
                            "periodSeconds": 10,
                            "failureThreshold": 6,
                        },
                        "startupProbe": {
                            "httpGet": {
                                "port": config.sessions.git_rpc_server.port,
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
    # NOTE: The oauth2proxy is used to authenticate requests for the sidecar
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
                        f"--upstream=http://127.0.0.1:{config.sessions.git_rpc_server.port}"
                        f"/sessions/{server.server_name}/sidecar/"
                    ),
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": (f"--skip-auth-route=^/sessions/{server.server_name}/sidecar/health$"),
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
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": (
                        f"--skip-auth-route=^/sessions/{server.server_name}/sidecar/jsonrpc/map$"
                    ),
                },
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/containers/1/args/-",
                    "value": "--oidc-extra-audience=renku",
                },
            ],
        }
    )
    # INFO: Add a k8s service so that the RPC server can be directly reached by the ui server
    patches.append(
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/serviceRpcServer",
                    "value": {
                        "apiVersion": "v1",
                        "kind": "Service",
                        "metadata": {
                            "name": f"{server.server_name}-rpc-server",
                            "namespace": server.k8s_client.preferred_namespace,
                        },
                        "spec": {
                            "ports": [
                                {
                                    "name": "http",
                                    "port": 80,
                                    "protocol": "TCP",
                                    "targetPort": config.sessions.git_rpc_server.port,
                                },
                            ],
                            "selector": {
                                "app": server.server_name,
                            },
                        },
                    },
                },
            ],
        }
    )

    return patches
