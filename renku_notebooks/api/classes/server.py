from dataclasses import asdict, dataclass
from functools import lru_cache
from itertools import chain
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urljoin, urlparse

from flask import current_app

from ...config import config
from ...errors.programming import ConfigurationError, DuplicateEnvironmentVariableError
from ...errors.user import MissingResourceError
from ...util.kubernetes_ import make_server_name
from ..amalthea_patches import cloudstorage as cloudstorage_patches
from ..amalthea_patches import general as general_patches
from ..amalthea_patches import git_proxy as git_proxy_patches
from ..amalthea_patches import git_sidecar as git_sidecar_patches
from ..amalthea_patches import init_containers as init_containers_patches
from ..amalthea_patches import inject_certificates as inject_certificates_patches
from ..amalthea_patches import jupyter_server as jupyter_server_patches
from ..amalthea_patches import ssh as ssh_patches
from ..schemas.server_options import ServerOptions
from .cloud_storage import ICloudStorageRequest
from .k8s_client import K8sClient
from .user import AnonymousUser, RegisteredUser


@dataclass
class Repository:
    """Information required to clone a repository."""

    namespace: str
    project: str
    branch: str
    commit_sha: str
    url: Optional[str] = None

    @classmethod
    def from_schema(cls, data: dict[str, str]) -> "Repository":
        return cls(
            namespace=data["namespace"],
            project=data["project"],
            branch=data["branch"],
            commit_sha=data["commit_sha"],
        )


class UserServer:
    """Represents a jupyter server session."""

    def __init__(
        self,
        user: Union[AnonymousUser, RegisteredUser],
        namespace: Optional[str],
        project: Optional[str],
        branch: Optional[str],
        commit_sha: Optional[str],
        notebook: Optional[str],  # TODO: Is this value actually needed?
        image: Optional[str],
        server_options: ServerOptions,
        environment_variables: dict[str, str],
        cloudstorage: list[ICloudStorageRequest],
        k8s_client: K8sClient,
        workspace_mount_path: Path,
        work_dir: Path,
        using_default_image: bool = False,
        is_image_private: bool = False,
        **_,
    ):
        self._check_flask_config()
        self._user = user
        self._k8s_client: K8sClient = k8s_client
        self.safe_username = self._user.safe_username  # type:ignore
        self.namespace = namespace
        self.project = project
        self.branch = branch
        self.commit_sha = commit_sha
        self.notebook = notebook
        self.image = image
        self.server_options = server_options
        self.environment_variables = environment_variables
        self.using_default_image = using_default_image
        self.git_host = urlparse(config.git.url).netloc
        self.workspace_mount_path = workspace_mount_path
        self.work_dir = work_dir
        self.cloudstorage: Optional[list[ICloudStorageRequest]] = cloudstorage
        self.gl_project_name = f"{self.namespace}/{self.project}"
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
        self._repositories: Optional[list[Repository]] = None

    @staticmethod
    def _check_flask_config():
        """Check the app config and ensure minimum required parameters are present."""
        if config.git.url is None:
            raise ConfigurationError(
                message="The gitlab URL is missing, it must be provided in " "an environment variable called GITLAB_URL"
            )
        if config.git.registry is None:
            raise ConfigurationError(
                message="The url to the docker image registry is missing, it must be provided in "
                "an environment variable called IMAGE_REGISTRY"
            )

    @property
    def gl_project(self):
        return self._user.get_renku_project(self.gl_project_name)

    @property
    def gl_project_path(self) -> Optional[str]:
        gl_project = self.gl_project
        return gl_project.path if gl_project else None

    @property
    def gl_project_url(self) -> Optional[str]:
        gl_project = self.gl_project
        return gl_project.http_url_to_repo if gl_project else None

    @property
    def repositories(self) -> list[dict[str, str]]:
        if self._repositories is None:
            self._repositories = [
                asdict(
                    Repository(
                        namespace=self.namespace,
                        project=self.project,
                        branch=self.branch,
                        commit_sha=self.commit_sha,
                        url=self.gl_project_url,
                    )
                )
            ]

        return self._repositories

    @property
    def server_name(self):
        """Make the name that is used to identify a unique user session."""
        return make_server_name(
            self._user.safe_username,
            self.namespace,
            self.project,
            self.branch,
            self.commit_sha,
        )

    @property
    def user(self) -> Union[AnonymousUser, RegisteredUser]:
        """Getter for server's user."""
        return self._user

    @property
    def user_is_anonymous(self) -> bool:
        """Return True if server's user is not registered."""
        return isinstance(self._user, AnonymousUser)

    @property
    def k8s_client(self) -> K8sClient:
        """Return server's k8s client."""
        return self._k8s_client

    @property
    @lru_cache(maxsize=8)
    def hibernation_allowed(self):
        return self._user and not self.user_is_anonymous

    def _branch_exists(self):
        """Check if a specific branch exists in the user's gitlab project.

        The branch name is not required by the API and therefore
        passing None to this function will return True.
        """
        if self.branch is not None and self.gl_project is not None:
            try:
                self.gl_project.branches.get(self.branch)
            except Exception as err:
                current_app.logger.warning(f"Branch {self.branch} cannot be verified or does not exist. {err}")
            else:
                return True
        return False

    def _commit_sha_exists(self):
        """Check if a specific commit sha exists in the user's gitlab project."""
        if self.commit_sha is not None and self.gl_project is not None:
            try:
                self.gl_project.commits.get(self.commit_sha)
            except Exception as err:
                current_app.logger.warning(f"Commit {self.commit_sha} cannot be verified or does not exist. {err}")
            else:
                return True
        return False

    def _get_patches(self):
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
                git_proxy_patches.main(self),
                git_sidecar_patches.main(self),
                general_patches.oidc_unverified_email(self),
                ssh_patches.main(),
                # init container for certs must come before all other init containers
                # so that it runs first before all other init containers
                init_containers_patches.certificates(),
                init_containers_patches.download_image(self),
                init_containers_patches.git_clone(self),
                inject_certificates_patches.proxy(self),
                # Cloud Storage needs to patch the git clone sidecar spec and so should come after
                # the sidecars
                # WARN: this patch depends on the index of the sidecar and so needs to be updated
                # if sidercars are added or removed
                cloudstorage_patches.main(self),
            )
        )

    def _get_session_manifest(self):
        """Compose the body of the user session for the k8s operator."""
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
                "size": (self.server_options.storage if config.sessions.storage.use_empty_dir_size_limit else ""),
                "pvc": {
                    "enabled": False,
                    "mountPath": self.workspace_mount_path.absolute().as_posix(),
                },
            }
        # Authentication
        if isinstance(self._user, RegisteredUser):
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
                        if isinstance(self._user, RegisteredUser)
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

    @staticmethod
    def _check_environment_variables_overrides(patches_list):
        """Check if any patch overrides server's environment variables.

        Checks if it overrides with a different value or if two patches create environment variables with different
        values.
        """
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
                            message=f"Environment variable {path}::{name} is being overridden by " "multiple patches"
                        )
                    else:
                        env_vars[key] = value

    def start(self) -> Optional[dict[str, Any]]:
        """Create the jupyterserver resource in k8s."""
        error = []
        if self.gl_project is None:
            error.append(f"project {self.project} does not exist")
        if not self._branch_exists():
            error.append(f"branch {self.branch} does not exist")
        if not self._commit_sha_exists():
            error.append(f"commit {self.commit_sha} does not exist")
        if self.image is None:
            error.append(f"image {self.image} does not exist or cannot be accessed")
        if len(error) == 0:
            js = self._k8s_client.create_server(self._get_session_manifest(), self.safe_username)
        else:
            raise MissingResourceError(
                message=(
                    "Cannot start the session because the following Git "
                    f"or Docker resources are missing: {', '.join(error)}"
                )
            )
        return js

    @property
    def server_url(self) -> str:
        """The URL where a user can access their session."""
        if isinstance(self._user, RegisteredUser):
            return urljoin(
                "https://" + config.sessions.ingress.host,
                f"sessions/{self.server_name}",
            )
        else:
            return urljoin(
                "https://" + config.sessions.ingress.host,
                f"sessions/{self.server_name}?token={self._user.username}",
            )

    def __str__(self):
        return (
            f"<UserServer user: {self._user.username} namespace: {self.namespace} "
            f"project: {self.project} commit: {self.commit_sha} image: {self.image}>"
        )

    def get_annotations(self):
        prefix = config.session_get_endpoint_annotations.renku_annotation_prefix
        annotations = {
            f"{prefix}commit-sha": self.commit_sha,
            f"{prefix}gitlabProjectId": None,
            f"{prefix}safe-username": self._user.safe_username,
            f"{prefix}username": self._user.username,
            f"{prefix}userId": self._user.id,
            f"{prefix}servername": self.server_name,
            f"{prefix}branch": self.branch,
            f"{prefix}git-host": self.git_host,
            f"{prefix}namespace": self.namespace,
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
        if self.gl_project is not None:
            annotations[f"{prefix}gitlabProjectId"] = str(self.gl_project.id)
            annotations[f"{prefix}repository"] = self.gl_project.web_url
        return annotations

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
        if self.gl_project is not None:
            labels[f"{prefix}gitlabProjectId"] = str(self.gl_project.id)
        return labels


class Renku2UserServer(UserServer):
    """Represents a Renku 2 jupyter server session."""

    def __init__(
        self,
        user: Union[AnonymousUser, RegisteredUser],
        notebook: Optional[str],  # TODO: Is this value actually needed?
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
        repositories: list[Repository],
        using_default_image: bool = False,
        is_image_private: bool = False,
        **_,
    ):
        super().__init__(
            user=user,
            namespace=None,
            project=None,
            branch=None,
            commit_sha=None,
            notebook=notebook,
            image=image,
            server_options=server_options,
            environment_variables=environment_variables,
            cloudstorage=cloudstorage,
            k8s_client=k8s_client,
            workspace_mount_path=workspace_mount_path,
            work_dir=work_dir,
            using_default_image=using_default_image,
            is_image_private=is_image_private,
        )
        self._server_name = server_name
        self.project_id = project_id
        self.launcher_id = launcher_id
        self._repositories: list[Repository] = repositories or []
        self._calculated_repository_urls: bool = False

    @property
    def gl_project(self):
        if len(self._repositories) == 1:
            project_path = f"{self._repositories[0].namespace}/{self._repositories[0].project}"
            return self._user.get_renku_project(project_path)
        return None

    @property
    def gl_project_path(self) -> Optional[str]:
        gl_project = self.gl_project
        return gl_project.path if gl_project else None

    @property
    def gl_project_url(self) -> Optional[str]:
        """Return the common hostname of all repositories."""
        repositories = self.repositories

        if not repositories:
            return ""
        elif len(repositories) == 1:
            return repositories[0]["url"]

        # NOTE: For more than one repository, we only support one gitlab instance atm
        return self._user.gitlab_client.url

    @property
    def server_name(self):
        """Make the name that is used to identify a unique user session."""
        return self._server_name

    @property
    def repositories(self) -> list[dict[str, str]]:
        if self._repositories and not self._calculated_repository_urls:
            for r in self._repositories:
                project = self._user.get_renku_project(f"{r.namespace}/{r.project}")
                if project:
                    r.url = project.http_url_to_repo

            self._calculated_repository_urls = True

        return [asdict(r) for r in self._repositories]

    def _branch_exists(self):
        """Check if a specific branch exists in the user's gitlab project.

        The branch name is not required by the API and therefore
        passing None to this function will return True.
        """
        raise NotImplementedError

    def _commit_sha_exists(self):
        """Check if a specific commit sha exists in the user's gitlab project."""
        raise NotImplementedError

    def get_annotations(self):
        annotations = super().get_annotations()

        # Add Renku 2.0 annotations
        prefix = config.session_get_endpoint_annotations.renku_annotation_prefix
        annotations[f"{prefix}renkuVersion"] = "2.0"
        annotations[f"{prefix}projectId"] = self.project_id
        annotations[f"{prefix}launcherId"] = self.launcher_id

        return annotations

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
                git_proxy_patches.main(self) if has_repository else [],
                git_sidecar_patches.main(self) if has_repository else [],
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

    def start(self) -> Optional[dict[str, Any]]:
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
