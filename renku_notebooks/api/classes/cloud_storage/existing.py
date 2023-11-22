from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ExistingCloudStorage:
    remote: str
    type: str

    @classmethod
    def from_manifest(cls, manifest: Dict[str, Any]) -> List["ExistingCloudStorage"]:
        output: List[ExistingCloudStorage] = []
        for patch_collection in manifest["spec"]["patches"]:
            for patch in patch_collection["patch"]:
                if patch["op"] == "test":
                    continue
                if not isinstance(patch["value"], dict):
                    continue
                is_persistent_volume = patch["value"].get("kind") == "PersistentVolume"
                is_rclone = (
                    patch["value"].get("spec", {}).get("csi", {}).get("driver", "") == "csi-rclone"
                )
                if isinstance(patch["value"], dict) and is_persistent_volume and is_rclone:
                    config = patch["value"]["spec"]["csi"]["volumeAttributes"][
                        "configData"
                    ].splitlines()
                    _, storage_type = next(
                        (line.strip().split("=") for line in config if line.startswith("type")),
                        (None, "Unknown"),
                    )
                    output.append(
                        cls(
                            remote=patch["value"]["spec"]["csi"]["volumeAttributes"]["remote"],
                            type=storage_type.strip(),
                        )
                    )
        return output
