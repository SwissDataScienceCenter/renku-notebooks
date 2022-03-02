import base64
from flask import current_app
import secrets


def main(server):
    patches = []
    # INFO: Add add the rpc server as sidecar to the user session
    patches.append(
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
                        "env": [
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
                        "resources": {
                            "requests": {"memory": "32Mi", "cpu": "50m"},
                            "limits": {"memory": "64Mi", "cpu": "100m"},
                        },
                        "securityContext": {
                            "allowPrivilegeEscalation": False,
                            "fsGroup": 100,
                            "runAsGroup": 100,
                            "runAsUser": 1000,
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
    )
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
