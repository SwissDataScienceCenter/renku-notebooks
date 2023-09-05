from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from renku_notebooks.api.classes.server import UserServer


class ICloudStorageRequest(ABC):
    @abstractproperty
    def exists(self) -> bool:
        pass

    @abstractproperty
    def mount_folder(self) -> str:
        pass

    @abstractproperty
    def source_folder(self) -> str:
        pass

    @abstractproperty
    def bucket(self) -> str:
        pass

    @abstractmethod
    def get_manifest_patch(
        self,
        base_name: str,
        server: "UserServer",
        labels: Dict[str, str] = {},
        annotations: Dict[str, str] = {},
    ) -> Dict[str, Any]:
        pass
