from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ...errors.intermittent import IntermittentError
from ...errors.programming import ConfigurationError
from ...errors.user import InvalidComputeResourceError
from ..schemas.server_options import ServerOptions
from .user import User


@dataclass
class CRACValidator:
    """Calls to the CRAC service to validate resource requests."""

    crac_url: str

    def __post_init__(self):
        self.crac_url = self.crac_url.rstrip("/")

    def validate_class_storage(
        self,
        user: User,
        class_id: int,
        storage: Optional[int] = None,
    ) -> ServerOptions:
        """Ensures that the resource class and storage requested is valid."""
        headers = None
        if user.access_token is not None:
            headers = {"Authorization": f"bearer {user.access_token}"}
        res = requests.get(self.crac_url + f"/classes/{class_id}", headers=headers)
        if res.status_code != 200:
            raise InvalidComputeResourceError(
                message="The requested resource class does not exist or you do not "
                "have the required permissions to access it."
            )
        res_class = res.json()
        if storage is None:
            storage = res_class.get("default_storage", 1)
        if storage < 1:
            raise InvalidComputeResourceError(
                message="Storage requests have to be greater than or equal to 1GB."
            )
        if storage > res_class.get("max_storage"):
            raise InvalidComputeResourceError(
                message="The requested storage surpasses the maximum value allowed."
            )
        # Memory and disk space in CRAC are assumed to be in gigabytes whereas
        # the notebook service assumes that if a plain number is used then it is bytes.
        options = ServerOptions.from_resource_class(res_class)
        options.storage = storage * 1000000000
        return options

    def get_default_class(self) -> Dict[str, Any]:
        res = requests.get(self.crac_url + "/resource_pools")
        if res.status_code != 200:
            raise IntermittentError(
                "The CRAC sent an unexpected response, please try again later."
            )
        pools = res.json()
        default_pools = [p for p in pools if p.get("default", False)]
        if len(default_pools) < 1:
            raise ConfigurationError("Cannot find the default resource pool.")
        default_pool = default_pools[0]
        default_classes = [
            cls for cls in default_pool.get("classes", []) if cls.get("default", False)
        ]
        if len(default_classes) < 1:
            raise ConfigurationError("Cannot find the default resource class.")
        return default_classes[0]

    def find_acceptable_class(
        self, user: User, requested_server_options: ServerOptions
    ) -> Optional[ServerOptions]:
        """Find a resource class that is available to the user that is greater than or equal to
        the old-style server options that the user requested."""
        headers = None
        if user.access_token is not None:
            headers = {"Authorization": f"bearer {user.access_token}"}
        res = requests.get(self.crac_url + "/resource_pools", headers=headers)
        if res.status_code != 200:
            raise IntermittentError(
                message="The compute resource access control service sent "
                "an unexpected response, please try again later",
            )
        resource_pools = res.json()
        # Difference and best candidate in the case that the resource class will be
        # greater than or equal to the request
        best_larger_or_equal_diff = None
        best_larger_or_equal_class = None
        zero_diff = ServerOptions(cpu=0, memory=0, gpu=0, storage=0)
        for resource_pool in resource_pools:
            for resource_class in resource_pool["classes"]:
                resource_class_mdl = ServerOptions.from_resource_class(resource_class)
                diff = resource_class_mdl - requested_server_options
                if diff >= zero_diff and (
                    best_larger_or_equal_diff is None
                    or diff < best_larger_or_equal_diff
                ):
                    best_larger_or_equal_diff = diff
                    best_larger_or_equal_class = resource_class
        return best_larger_or_equal_class
