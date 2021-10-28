from flask import current_app

from ..classes.user import RegisteredUser


def tolerations():
    patches = []
    tolerations = [
        {
            "key": f"{current_app.config['RENKU_ANNOTATION_PREFIX']}dedicated",
            "operator": "Equal",
            "value": "user",
            "effect": "NoSchedule",
        }
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


def test(server):
    """RFC 6901 patches support test statements that will cause the whole patch
    to fail if the test statements are not correct. This is used to ensure that the
    order of containers in the amalthea manifests is what the notebook service expects."""
    patches = []
    container_names = (
        current_app.config["AMALTHEA_CONTAINER_ORDER_REGISTERED_SESSION"]
        if type(server._user) is RegisteredUser
        else current_app.config["AMALTHEA_CONTAINER_ORDER_ANONYMOUS_SESSION"]
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


def oidc_unverified_email(server):
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
                            "value": current_app.config["OIDC_ALLOW_UNVERIFIED_EMAIL"],
                        },
                    },
                ],
            }
        )
    return patches
