from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class K8sUserSecrets:
    """Class containing the information for the Kubernetes secret that will
    provide the user secrets
    """

    name: str  # Name of the k8s secret containing the user secrets
    user_secret_ids: List[str]  # List of user secret ids
    mount_path: Path  # Path in the container where to mount the k8s secret
