from typing import TYPE_CHECKING

from ..classes.user import RegisteredUser
from ...config import config

if TYPE_CHECKING:
    from renku_notebooks.api.classes.server import UserServer


def session_tolerations():
    patches = []
    tolerations = [
        {
            "key": f"{config.session_get_endpoint_annotations.renku_annotation_prefix}dedicated",
            "operator": "Equal",
            "value": "user",
            "effect": "NoSchedule",
        },
        *config.sessions.tolerations,
    ]
    patches.append(
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/tolerations",
                    "value": tolerations,
                }
            ],
        }
    )
    return patches


def termination_grace_period():
    return [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/terminationGracePeriodSeconds",
                    "value": config.sessions.termination_grace_period_seconds,
                }
            ],
        }
    ]


def session_affinity():
    return [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/affinity",
                    "value": config.sessions.tolerations,
                }
            ],
        }
    ]


def session_node_selector():
    return [
        {
            "type": "application/json-patch+json",
            "patch": [
                {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/nodeSelector",
                    "value": config.sessions.node_selector,
                }
            ],
        }
    ]


def test(server: "UserServer"):
    """RFC 6901 patches support test statements that will cause the whole patch
    to fail if the test statements are not correct. This is used to ensure that the
    order of containers in the amalthea manifests is what the notebook service expects."""
    patches = []
    container_names = (
        config.sessions.container_order_anonymous
        if type(server._user) is RegisteredUser
        else config.sessions.container_order_registered
    )
    for container_ind, container_name in enumerate(container_names):
        patches.append(
            {
                "type": "application/json-patch+json",
                "patch": [
                    {
                        "op": "test",
                        "path": (
                            "/statefulset/spec/template/spec"
                            f"/containers/{container_ind}/name"
                        ),
                        "value": container_name,
                    }
                ],
            }
        )
    return patches


def oidc_unverified_email(server: "UserServer"):
    patches = []
    if type(server._user) is RegisteredUser:
        # modify oauth2 proxy to accept users whose email has not been verified
        # usually enabled for dev purposes
        patches.append(
            {
                "type": "application/json-patch+json",
                "patch": [
                    {
                        "op": "add",
                        "path": "/statefulset/spec/template/spec/containers/1/env/-",
                        "value": {
                            "name": "OAUTH2_PROXY_INSECURE_OIDC_ALLOW_UNVERIFIED_EMAIL",
                            "value": config.sessions.oidc.allow_unverified_email,
                        },
                    },
                ],
            }
        )
    return patches
