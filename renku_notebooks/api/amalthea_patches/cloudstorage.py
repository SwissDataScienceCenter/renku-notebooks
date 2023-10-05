from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from renku_notebooks.api.classes.cloud_storage import ICloudStorageRequest
    from renku_notebooks.api.classes.server import UserServer


def main(server: "UserServer") -> List[Dict[str, Any]]:
    cloud_storage_patches: List[Dict[str, Any]] = []
    cloud_storage_request: "ICloudStorageRequest"
    if not server.cloudstorage:
        return []
    for i, cloud_storage_request in enumerate(server.cloudstorage):
        cloud_storage_patches.append(cloud_storage_request.get_manifest_patch(server, i))
        cloud_storage_patches.append(
            {
                    "op": "add",
                    "path": "/statefulset/spec/template/spec/initContainers/2/env/-",
                    "value": {
                        "name": f"GIT_CLONE_S3_MOUNT_{i}",
                        "value": cloud_storage_request.mount_folder,
                    },
                },
        )
    return cloud_storage_patches
