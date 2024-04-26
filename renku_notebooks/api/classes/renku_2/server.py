from itertools import chain
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from ....config import config
from ....errors.programming import DuplicateEnvironmentVariableError
from ....errors.user import MissingResourceError
from ...amalthea_patches import cloudstorage as cloudstorage_patches
from ...amalthea_patches import general as general_patches
from ...amalthea_patches import init_containers as init_containers_patches
from ...amalthea_patches import \
    inject_certificates as inject_certificates_patches
from ...amalthea_patches import jupyter_server as jupyter_server_patches
from ...amalthea_patches import ssh as ssh_patches
from ...schemas.server_options import ServerOptions
from ..cloud_storage import ICloudStorageRequest
from ..k8s_client import K8sClient
from ..server import UserServer as Renku1UserServer
from ..user import AnonymousUser, RegisteredUser


class Renku2UserServer:
    """Represents a Renku 2.0 server session."""

    def __init__(
        self,
        user: AnonymousUser | RegisteredUser,
        image: str,
        project_id: str,
        launcher_id: str,
        server_name: str,
        server_options: ServerOptions,
        environment_variables: dict[str, str],
        cloudstorage: list[ICloudStorageRequest],
        k8s_client: K8sClient,
        workspace_mount_path: Path,
        work_dir: Path,
        # repositories: list[Repository],
        using_default_image: bool = False,
        is_image_private: bool = False,
        **_,
    ):
        Renku1UserServer._check_flask_config()
        self._user = user
        self._k8s_client: K8sClient = k8s_client
        self.safe_username = self._user.safe_username
        self.image = image
        self.server_options = server_options
        self.environment_variables = environment_variables
        self.using_default_image = using_default_image
        self.workspace_mount_path = workspace_mount_path
        self.work_dir = work_dir
        self.cloudstorage: list[ICloudStorageRequest] | None = cloudstorage
        self.is_image_private = is_image_private
        self.idle_seconds_threshold: int = (
            config.sessions.culling.registered.idle_seconds
            if isinstance(self._user, RegisteredUser)
            else config.sessions.culling.anonymous.idle_seconds
        )
        self.hibernated_seconds_threshold: int = (
            config.sessions.culling.registered.hibernated_seconds
            if isinstance(user, RegisteredUser)
            else config.sessions.culling.anonymous.hibernated_seconds
        )
        # self._repositories: Optional[List[Repository]] = None

        self.server_name = server_name
        self.project_id = project_id
        self.launcher_id = launcher_id
        # self._repositories: List[Repository] = repositories or []
        # self._calculated_repository_urls: bool = False

    @property
    def user(self) -> AnonymousUser | RegisteredUser:
        """Getter for server's user."""
        return self._user

    @property
    def k8s_client(self) -> K8sClient:
        """Return server's k8s client."""
        return self._k8s_client

    @property
    def server_url(self) -> str:
        """The URL where a user can access their session."""
        if type(self._user) is RegisteredUser:
            return urljoin(
                "https://" + config.sessions.ingress.host,
                f"sessions/{self.server_name}",
            )
        return urljoin(
            "https://" + config.sessions.ingress.host,
            f"sessions/{self.server_name}?token={self._user.username}",
        )

    @property
    def gl_project(self) -> None:
        return None

    @property
    def gl_project_path(self) -> None:
        return None

    @property
    def commit_sha(self) -> str:
        return ""

    @property
    def project(self) -> None:
        return None

    def __str__(self):
        return f"<UserServer user: {self._user.username} server_name: {self.server_name}>"

    def start(self) -> dict[str, Any] | None:
        """Create the jupyterserver resource in k8s."""
        if self.image is None:
            errors = [f"image {self.image} does not exist or cannot be accessed"]
            raise MissingResourceError(
                message=(
                    "Cannot start the session because the following Git "
                    f"or Docker resources are missing: {', '.join(errors)}"
                )
            )

        return self._k8s_client.create_server(self._get_session_manifest(), self.safe_username)

    def _get_session_manifest(self):
        """Compose the body of the user session for the k8s operator"""
        patches = self._get_patches()
        self._check_environment_variables_overrides(patches)

        # Storage
        if config.sessions.storage.pvs_enabled:
            storage = {
                "size": self.server_options.storage,
                "pvc": {
                    "enabled": True,
                    "storageClassName": config.sessions.storage.pvs_storage_class,
                    "mountPath": self.workspace_mount_path.absolute().as_posix(),
                },
            }
        else:
            storage = {
                "size": (
                    self.server_options.storage
                    if config.sessions.storage.use_empty_dir_size_limit
                    else ""
                ),
                "pvc": {
                    "enabled": False,
                    "mountPath": self.workspace_mount_path.absolute().as_posix(),
                },
            }
        # Authentication
        if type(self._user) is RegisteredUser:
            session_auth = {
                "token": "",
                "oidc": {
                    "enabled": True,
                    "clientId": config.sessions.oidc.client_id,
                    "clientSecret": {"value": config.sessions.oidc.client_secret},
                    "issuerUrl": self._user.oidc_issuer,
                    "authorizedEmails": [self._user.email],
                },
            }
        else:
            session_auth = {
                "token": self._user.username,
                "oidc": {"enabled": False},
            }
        # Combine everything into the manifest
        manifest = {
            "apiVersion": f"{config.amalthea.group}/{config.amalthea.version}",
            "kind": "JupyterServer",
            "metadata": {
                "name": self.server_name,
                "labels": self.get_labels(),
                "annotations": self.get_annotations(),
            },
            "spec": {
                "auth": session_auth,
                "culling": {
                    "idleSecondsThreshold": self.idle_seconds_threshold,
                    "maxAgeSecondsThreshold": (
                        config.sessions.culling.registered.max_age_seconds
                        if type(self._user) is RegisteredUser
                        else config.sessions.culling.anonymous.max_age_seconds
                    ),
                    "hibernatedSecondsThreshold": self.hibernated_seconds_threshold,
                },
                "jupyterServer": {
                    "defaultUrl": self.server_options.default_url,
                    "image": self.image,
                    "rootDir": self.work_dir.absolute().as_posix(),
                    "resources": self.server_options.to_k8s_resources(
                        enforce_cpu_limits=config.sessions.enforce_cpu_limits
                    ),
                },
                "routing": {
                    "host": urlparse(self.server_url).netloc,
                    "path": urlparse(self.server_url).path,
                    "ingressAnnotations": config.sessions.ingress.annotations,
                    "tls": {
                        "enabled": config.sessions.ingress.tls_secret is not None,
                        "secretName": config.sessions.ingress.tls_secret,
                    },
                },
                "storage": storage,
                "patches": patches,
            },
        }
        return manifest

    def _get_patches(self):
        has_repository = bool(self._repositories)

        return list(
            chain(
                general_patches.test(self),
                general_patches.session_tolerations(self),
                general_patches.session_affinity(self),
                general_patches.session_node_selector(self),
                general_patches.priority_class(self),
                general_patches.dev_shm(self),
                jupyter_server_patches.args(),
                jupyter_server_patches.env(self),
                jupyter_server_patches.image_pull_secret(self),
                jupyter_server_patches.disable_service_links(),
                jupyter_server_patches.rstudio_env_variables(self),
                # git_proxy_patches.main(self) if has_repository else [],
                # git_sidecar_patches.main(self) if has_repository else [],
                general_patches.oidc_unverified_email(self),
                ssh_patches.main(),
                # init container for certs must come before all other init containers
                # so that it runs first before all other init containers
                init_containers_patches.certificates(),
                init_containers_patches.download_image(self),
                init_containers_patches.git_clone(self) if has_repository else [],
                inject_certificates_patches.proxy(self),
                # Cloud Storage needs to patch the git clone sidecar spec and so should come after
                # the sidecars
                # WARN: this patch depends on the index of the sidecar and so needs to be updated
                # if sidercars are added or removed
                cloudstorage_patches.main(self),
            )
        )

    @staticmethod
    def _check_environment_variables_overrides(patches_list):
        """Check if any patch overrides server's environment variables with a different value,
        or if two patches create environment variables with different values."""
        env_vars = {}

        for patch_list in patches_list:
            patches = patch_list["patch"]

            for patch in patches:
                path = patch["path"].lower()
                if path.endswith("/env/-"):
                    name = patch["value"]["name"]
                    value = patch["value"]["value"]
                    key = (path, name)

                    if key in env_vars and env_vars[key] != value:
                        raise DuplicateEnvironmentVariableError(
                            message=f"Environment variable {path}::{name} is being overridden by "
                            "multiple patches"
                        )
                    else:
                        env_vars[key] = value

    def get_labels(self):
        prefix = config.session_get_endpoint_annotations.renku_annotation_prefix
        labels = {
            "app": "jupyter",
            "component": "singleuser-server",
            f"{prefix}commit-sha": self.commit_sha,
            f"{prefix}gitlabProjectId": None,
            f"{prefix}safe-username": self._user.safe_username,
            f"{prefix}quota": self.server_options.priority_class,
            f"{prefix}userId": self._user.id,
        }
        return labels

    def get_annotations(self):
        prefix = config.session_get_endpoint_annotations.renku_annotation_prefix
        annotations = {
            f"{prefix}commit-sha": self.commit_sha,
            f"{prefix}gitlabProjectId": None,
            f"{prefix}safe-username": self._user.safe_username,
            f"{prefix}username": self._user.username,
            f"{prefix}userId": self._user.id,
            f"{prefix}servername": self.server_name,
            f"{prefix}branch": None,
            f"{prefix}git-host": None,
            f"{prefix}namespace": None,
            f"{prefix}projectName": self.project,
            f"{prefix}requested-image": self.image,
            f"{prefix}repository": None,
            f"{prefix}hibernation": "",
            f"{prefix}hibernationBranch": "",
            f"{prefix}hibernationCommitSha": "",
            f"{prefix}hibernationDirty": "",
            f"{prefix}hibernationSynchronized": "",
            f"{prefix}hibernationDate": "",
            f"{prefix}hibernatedSecondsThreshold": str(self.hibernated_seconds_threshold),
            f"{prefix}lastActivityDate": "",
            f"{prefix}idleSecondsThreshold": str(self.idle_seconds_threshold),
        }
        if self.server_options.resource_class_id:
            annotations[f"{prefix}resourceClassId"] = str(self.server_options.resource_class_id)

        # Add Renku 2.0 annotations
        annotations[f"{prefix}renkuVersion"] = "2.0"
        annotations[f"{prefix}projectId"] = self.project_id
        annotations[f"{prefix}launcherId"] = self.launcher_id

        return annotations
