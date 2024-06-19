from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from renku_notebooks.api.classes.cloud_storage import ICloudStorageRequest
    from renku_notebooks.api.classes.server import UserServer


def main(server: "UserServer") -> list[dict[str, Any]]:
    cloud_storage_patches: list[dict[str, Any]] = []
    cloud_storage_request: ICloudStorageRequest
    if not server.cloudstorage:
        return []
    for i, cloud_storage_request in enumerate(server.cloudstorage):
        cloud_storage_patches.extend(
            cloud_storage_request.get_manifest_patch(
                f"{server.server_name}-ds-{i}", server.k8s_client.preferred_namespace
            )
        )
        if server.repositories:
            cloud_storage_patches.append(
                {
                    "type": "application/json-patch+json",
                    "patch": [
                        {
                            "op": "add",
                            "path": "/statefulset/spec/template/spec/initContainers/2/env/-",
                            "value": {
                                "name": f"GIT_CLONE_STORAGE_MOUNTS_{i}",
                                "value": cloud_storage_request.mount_folder,
                            },
                        },
                    ],
                },
            )
    return cloud_storage_patches
