from flask.globals import current_app
import requests
from kubernetes import client
from kubernetes.client.rest import ApiException
import base64
import json
from urllib.parse import urlparse
from uuid import uuid4
from flask import make_response, jsonify
import logging
from urllib.parse import urljoin


from ...util.check_image import parse_image_name, get_docker_token, image_exists
from ...util.kubernetes_ import (
    get_k8s_client,
    secret_exists,
    filter_pods_by_annotations,
    make_server_name,
)
from .storage import SessionPVC


class UserServer:
    """Represents a jupuyterhub session."""

    def __init__(
        self,
        user,
        namespace,
        project,
        branch,
        commit_sha,
        notebook,
        image,
        server_options,
    ):
        self._renku_annotation_prefix = "renku.io/"
        self._check_flask_config()
        self._user = user
        self._k8s_client, self._k8s_namespace = get_k8s_client()
        self.safe_username = self._user.safe_username
        self.namespace = namespace
        self.project = project
        self.branch = branch
        self.commit_sha = commit_sha
        self.notebook = notebook
        self.image = image
        self.server_options = server_options
        self.using_default_image = self.image == current_app.config.get("DEFAULT_IMAGE")
        self.session_pvc = (
            SessionPVC(
                self._user, self.namespace, self.project, self.branch, self.commit_sha
            )
            if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]
            else None
        )

    def _check_flask_config(self):
        """Check the app config and ensure minimum required parameters are present."""
        if current_app.config.get("JUPYTERHUB_API_TOKEN", None) is None:
            raise ValueError(
                "The jupyterhub API token is missing, it must be provided in "
                "an environment variable called JUPYTERHUB_API_TOKEN"
            )
        if current_app.config.get("GITLAB_URL", None) is None:
            raise ValueError(
                "The gitlab URL is missing, it must be provided in "
                "an environment variable called GITLAB_URL"
            )
        if current_app.config.get("IMAGE_REGISTRY", None) is None:
            raise ValueError(
                "The url to the docker image registry is missing, it must be provided in "
                "an environment variable called IMAGE_REGISTRY"
            )

    @property
    def server_name(self):
        """Make the server that JupyterHub uses to identify a unique user session"""
        return make_server_name(
            self.namespace, self.project, self.branch, self.commit_sha
        )

    def _project_exists(self):
        """Retrieve the GitLab project."""
        try:
            self._user.get_renku_project(f"{self.namespace}/{self.project}")
        except Exception:
            return False
        else:
            return True

    def _branch_exists(self):
        """Check if a specific branch exists in the user's gitlab
        project. The branch name is not required by the API and therefore
        passing None to this function will return True."""
        if self.branch is not None:
            try:
                self._user.get_renku_project(
                    f"{self.namespace}/{self.project}"
                ).branches.get(self.branch)
            except Exception:
                return False
            else:
                return True
        return True

    def _commit_sha_exists(self):
        """Check if a specific commit sha exists in the user's gitlab project"""
        try:
            self._user.get_renku_project(
                f"{self.namespace}/{self.project}"
            ).commits.get(self.commit_sha)
        except Exception:
            return False
        else:
            return True

    def _get_image(self, image):
        """Set the notebook image if not specified in the request. If specific image
        is requested then confirm it exists and it can be accessed."""
        gl_project = self._user.get_renku_project(f"{self.namespace}/{self.project}")
        if image is None:
            parsed_image = {
                "hostname": current_app.config.get("IMAGE_REGISTRY"),
                "image": gl_project.path_with_namespace.lower(),
                "tag": self.commit_sha[:7],
            }
            commit_image = (
                f"{current_app.config.get('IMAGE_REGISTRY')}/"
                f"{gl_project.path_with_namespace.lower()}"
                f":{self.commit_sha[:7]}"
            )
        else:
            parsed_image = parse_image_name(image)
        # get token
        token, is_image_private = get_docker_token(**parsed_image, user=self._user)
        # check if images exist
        image_exists_result = image_exists(**parsed_image, token=token)
        # assign image
        if image_exists_result and image is None:
            # the image tied to the commit exists
            verified_image = commit_image
        elif not image_exists_result and image is None:
            # the image tied to the commit does not exist, fallback to default image
            verified_image = current_app.config.get("DEFAULT_IMAGE")
            is_image_private = False
            print(
                f"Image for the selected commit {self.commit_sha} of {self.project}"
                " not found, using default image "
                f"{current_app.config.get('DEFAULT_IMAGE')}"
            )
        elif image_exists_result and image is not None:
            # a specific image was requested and it exists
            verified_image = image
        else:
            return None, None
        self.using_default_image = verified_image == current_app.config["DEFAULT_IMAGE"]
        return verified_image, is_image_private

    def _get_registry_secret(self, b64encode=True):
        """If an image from gitlab is used and the image is not public
        create an image pull secret in k8s so that the private image can be used."""
        payload = {
            "auths": {
                current_app.config.get("IMAGE_REGISTRY"): {
                    "Username": "oauth2",
                    "Password": self._user.oauth_token,
                    "Email": str(
                        self._user.hub_user.get("auth_state", {})
                        .get("gitlab_user", {})
                        .get("email")
                    ),
                }
            }
        }
        output = json.dumps(payload)
        if b64encode:
            return base64.b64encode(output.encode()).decode()
        return output

    def _get_session_manifest(self):
        """Compose the body of the user session for the k8s operator"""
        gl_project = self._user.get_renku_project(f"{self.namespace}/{self.project}")
        resource_modifications = [
            {
                "modification": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "env": [
                                            {
                                                "name": "MOUNT_PATH",
                                                "value": "/work/private-lfs-auth",
                                            },
                                            {
                                                "name": "REPOSITORY",
                                                "value": gl_project.http_url_to_repo,
                                            },
                                            {"name": "LFS_AUTO_FETCH", "value": self.server_options["lfs-autofetch"]},
                                            {
                                                "name": "COMMIT_SHA",
                                                "value": self.commit_sha,
                                            },
                                            {"name": "BRANCH", "value": "master"},
                                            {
                                                # used only for naming autosave branch
                                                "name": "JUPYTERHUB_USER",
                                                "value": self._user.username,
                                            },
                                            {"name": "GIT_AUTOSAVE", "value": "1"},
                                            {
                                                "name": "GIT_URL",
                                                "value": current_app.config.GITLAB_URL,
                                            },
                                        ],
                                        "image": "ableuler/py-git:latest",
                                        "name": "git-sidecar",
                                        "ports": [
                                            {
                                                "containerPort": 4000,
                                                "name": "git-port",
                                                "protocol": "TCP",
                                            }
                                        ],
                                        "resources": {},
                                        "securityContext": {
                                            "allowPrivilegeEscalation": False,
                                            "fsGroup": 100,
                                            "runAsGroup": 100,
                                            "runAsUser": 1000,
                                        },
                                        "volumeMounts": [
                                            {
                                                "mountPath": "/work",
                                                "name": "workspace",
                                                "subPath": "work",
                                            }
                                        ],
                                    },
                                    {
                                        "env": [
                                            {
                                                "name": "GITLAB_OAUTH_TOKEN",
                                                "value": "fds",
                                            },
                                            {
                                                "name": "REPOSITORY_URL",
                                                "value": gl_project.http_url_to_repo,
                                            },
                                            {
                                                "name": "MITM_PROXY_PORT",
                                                "value": "8080",
                                            },
                                        ],
                                        "image": "ableuler/git-proxy:latest",
                                        "name": "git-proxy",
                                    },
                                ],
                                "imagePullSecrets": [
                                    {"name": self.server_name + "-secret"}
                                ],
                            }
                        }
                    }
                },
                "resource": "statefulset",
            },
            {
                "modification": {
                    "spec": {
                        "ports": [
                            {
                                "name": "git-service",
                                "port": 4000,
                                "protocol": "TCP",
                                "targetPort": 4000,
                            }
                        ]
                    }
                },
                "resource": "service",
            },
        ]
        starter = {
            "apiVersion": "renku.io/v1alpha1",
            "kind": "JupyterServer",
            "metadata": {"name": self.server_name},
            "spec": {
                "auth": {
                    "cookieWhiteList": ["username-localhost-8888", "_xsrf"],
                    "oidc": {
                        "enabled": True,
                        "clientId": current_app.config.OIDC_CLIENT_ID,
                        "clientSecret": self._user.keycloak_access_token,
                        "issuerUrl": current_app.config.OIDC_ISSUER_URL,
                        "userId": self._user.keycloak_id_token,
                    },
                },
                "extraResources": [
                    {
                        "api": "CoreV1Api",
                        "creationMethod": "create_namespaced_secret",
                        "resourceSpec": {
                            "apiVersion": "v1",
                            "data": {".dockerconfigjson": self._get_registry_secret()},
                            "kind": "Secret",
                            "metadata": {
                                "name": self.server_name + "-secret",
                                "namespace": self._k8s_namespace,
                            },
                            "type": "kubernetes.io/dockerconfigjson",
                        },
                    }
                ],
                "jupyterServer": {
                    "defaultUrl": self.server_options["defaultUrl"],
                    "image": self.image,
                    "rootDir": "/home/jovyan/work/",
                },
                "resourceModifications": resource_modifications,
                "routing": {
                    "host": current_app.config.SESSIONS_HOST,
                    "path": f"/{self.server_name}",
                },
                "volume": {"size": "100Mi", "storageClass": "temporary"},
            },
        }
        return starter

    def start(self):
        """Sends a request to jupyterhub to start the server and returns a tuple
        that contains the jupyterhub response and an eror message (if applicable).
        If the git project, branch, commit sha and docker image exist, then the
        jupyterhub API response is returned, with None for the error message.
        But if some of the required elements (project, branch, commit, etc) do not
        exist, then the response is None and an error message is returned."""
        if (
            self._project_exists()
            and self._branch_exists()
            and self._commit_sha_exists()
        ):
            api_instance = client.CustomObjectsApi(self._k8s_client)
            api_instance.create_namespaced_custom_object(
                group="renku.io",
                version="v1alpha1",
                namespace=self._k8s_namespace,
                plural="jupyterservers",
                body=self._get_session_manifest(),
            )

    def server_exists(self):
        """Check if the user server exists (i.e. is an actual pod in k8s)."""
        return self.pod is not None

    @property
    def pod(self):
        """Get k8s pod for the user server. If no pods are found return None, if
        exactly 1 pod is found then return that pod. Lastly, if more than one pods
        are found that match the user information/parameters raise an exception, this
        should never happen."""
        pods = self._user.pods
        pods = filter_pods_by_annotations(
            pods, {"hub.jupyter.org/servername": self.server_name}
        )
        if len(pods) == 0:
            return None
        elif len(pods) == 1:
            return pods[0]
        else:  # more than one pod was matched
            raise Exception(
                f"The user session matches {len(pods)} k8s pods, "
                "it should match only one."
            )

    def stop(self, forced=False):
        """Stop user's server with specific name"""
        pod_name = self.pod.metadata.name
        if forced:
            try:
                self._k8s_client.delete_namespaced_pod(
                    pod_name, self._k8s_namespace, grace_period_seconds=30
                )
                if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]:
                    self.session_pvc.delete()
                return make_response("", 204)
            except ApiException as e:
                logging.warning(
                    f"Cannot delete server: {pod_name} for user: "
                    f"{self._user.hub_username}, error: {e}"
                )
                return make_response(
                    jsonify({"messages": {"error": "Cannot force delete server"}}), 400
                )
        else:
            r = requests.delete(
                f"{current_app.config['JUPYTERHUB_URL']}/users/"
                f"{self._user.hub_username}/servers/{self.server_name}",
                headers=current_app.config["JUPYTERHUB_ADMIN_HEADERS"],
            )

            # If the server was deleted gracefully, remove the PVC if it exists
            if r.status_code < 300:
                if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]:
                    self.session_pvc.delete()

            if r.status_code == 204:
                return make_response("", 204)
            elif r.status_code == 202:
                return make_response(
                    jsonify(
                        {
                            "messages": {
                                "information": "The server was not stopped, "
                                "it is taking a while to stop."
                            }
                        }
                    ),
                    r.status_code,
                )
            else:
                message = r.json().get(
                    "message", "Something went wrong while tring to stop the server"
                )
                return make_response(
                    jsonify({"messages": {"error": message}}), r.status_code
                )

    def get_logs(self, max_log_lines=0, container_name="notebook"):
        """Get the logs of the k8s pod that runs the user server."""
        if self.pod is None:
            return None
        pod_name = self.pod.metadata.name
        if max_log_lines == 0:
            logs = self._k8s_client.read_namespaced_pod_log(
                pod_name, self._k8s_namespace, container=container_name
            )
        else:
            logs = self._k8s_client.read_namespaced_pod_log(
                pod_name,
                self._k8s_namespace,
                tail_lines=max_log_lines,
                container=container_name,
            )
        return logs

    def _cleanup_pvcs_autosave(self):
        namespace_project = f"{self.namespace}/{self.project}"
        autosaves = self._user.get_autosaves(namespace_project)
        for autosave in autosaves:
            autosave.cleanup(self.commit_sha)

    @property
    def server_url(self):
        """The URL where a user can access their session."""
        pod = self.pod
        url = "{jh_path_prefix}/user/{username}/{servername}/".format(
            jh_path_prefix=current_app.config.get("JUPYTERHUB_PATH_PREFIX").rstrip("/"),
            username=pod.metadata.annotations["hub.jupyter.org/username"],
            servername=pod.metadata.annotations["hub.jupyter.org/servername"],
        )
        return urljoin(current_app.config.get("JUPYTERHUB_ORIGIN"), url)

    @classmethod
    def from_pod(cls, user, pod):
        """Create a Server instance from a k8s pod object."""
        renku_annotation_prefix = "renku.io/"
        image = None
        for container in pod.spec.containers:
            if container.name == "notebook":
                image = container.image
        return cls(
            user,
            pod.metadata.annotations.get(renku_annotation_prefix + "namespace"),
            pod.metadata.annotations.get(renku_annotation_prefix + "projectName"),
            pod.metadata.annotations.get(renku_annotation_prefix + "branch"),
            pod.metadata.annotations.get(renku_annotation_prefix + "commit-sha"),
            None,
            image,
            {},
        )

    @classmethod
    def from_server_name(cls, user, server_name):
        """Create a Server instance from a Jupyterhub server name."""
        pods = user.pods
        pods = filter_pods_by_annotations(
            pods, {"hub.jupyter.org/servername": server_name}
        )
        if len(pods) != 1:
            return None
        pod = pods[0]
        return cls.from_pod(user, pod)
