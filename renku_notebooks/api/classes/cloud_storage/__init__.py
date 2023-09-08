from abc import ABC, abstractmethod, abstractproperty
from typing import TYPE_CHECKING, Any, Dict

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
        server: "UserServer",
        index: int,
        labels: Dict[str, str] = {},
        annotations: Dict[str, str] = {},
    ) -> Dict[str, Any]:
        pass
