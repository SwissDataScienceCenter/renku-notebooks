from flask.globals import current_app
import requests
from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.client.models.v1_resource_requirements import V1ResourceRequirements
from hashlib import md5
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
)
from ...util.file_size import parse_file_size


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

    def _check_flask_config(self):
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
        return self.make_server_name(
            self.namespace, self.project, self.branch, self.commit_sha
        )

    @staticmethod
    def make_server_name(namespace, project, branch, commit_sha):
        """Form a 16-digit hash server ID."""
        server_string = f"{namespace}{project}{branch}{commit_sha}"
        return "{project}-{hash}".format(
            project=project[:54], hash=md5(server_string.encode()).hexdigest()[:8]
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
        # the branch name is not required by the API and therefore
        # passing None to this function will return True
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
        try:
            self._user.get_renku_project(
                f"{self.namespace}/{self.project}"
            ).commits.get(self.commit_sha)
        except Exception:
            return False
        else:
            return True

    def _get_image(self, image):
        # set the notebook image if not specified in the request
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

    def _create_registry_secret(self):
        secret_name = f"{self.safe_username}-registry-{str(uuid4())}"
        git_host = urlparse(current_app.config.get("GITLAB_URL")).netloc
        gitlab_project_id = self._user.gitlab_client.projects.get(
            f"{self.namespace}/{self.project}"
        ).id
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

        data = {
            ".dockerconfigjson": base64.b64encode(json.dumps(payload).encode()).decode()
        }

        secret = client.V1Secret(
            api_version="v1",
            data=data,
            kind="Secret",
            metadata={
                "name": secret_name,
                "namespace": self._k8s_namespace,
                "annotations": {
                    self._renku_annotation_prefix + "git-host": git_host,
                    self._renku_annotation_prefix + "namespace": self.namespace,
                    self._renku_annotation_prefix + "username": self.safe_username,
                },
                "labels": {
                    "component": "singleuser-server",
                    self._renku_annotation_prefix + "username": self.safe_username,
                    self._renku_annotation_prefix + "commit-sha": self.commit_sha,
                    self._renku_annotation_prefix
                    + "gitlabProjectId": str(gitlab_project_id),
                },
            },
            type="kubernetes.io/dockerconfigjson",
        )

        if secret_exists(secret_name, self._k8s_client, self._k8s_namespace):
            self._k8s_client.replace_namespaced_secret(
                secret_name, self._k8s_namespace, secret
            )
        else:
            self._k8s_client.create_namespaced_secret(self._k8s_namespace, body=secret)

        return secret

    def _get_start_payload(self):
        verified_image, is_image_private = self._get_image(self.image)
        if verified_image is None:
            return None
        gl_project = self._user.gitlab_client.projects.get(
            f"{self.namespace}/{self.project}"
        )
        payload = {
            "namespace": self.namespace,
            "project": self.project,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "project_id": gl_project.id,
            "notebook": self.notebook,
            "image": verified_image,
            "git_clone_image": current_app.config["GIT_CLONE_IMAGE"],
            "git_https_proxy_image": current_app.config["GIT_HTTPS_PROXY_IMAGE"],
            "server_options": self.server_options,
        }

        if current_app.config["GITLAB_AUTH"] and is_image_private:
            secret = self._create_registry_secret()
            payload["image_pull_secrets"] = [secret.metadata["name"]]

        if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]:
            pvc_exists = self.get_pvc() is not None
            if not pvc_exists:
                self._create_pvc(
                    storage_size=self.server_options.get("disk_request"),
                    storage_class=current_app.config[
                        "NOTEBOOKS_SESSION_PVS_STORAGE_CLASS"
                    ],
                )
            payload["pvc_name"] = self._pvc_name
            payload["pvc_exists"] = pvc_exists
        return payload

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
            payload = self._get_start_payload()
            if payload is None:
                return None, f"Cannot find/access image {self.image}."

            res = requests.post(
                f"{current_app.config['JUPYTERHUB_URL']}/users/"
                f"{self._user.hub_username}/servers/{self.server_name}",
                json=payload,
                headers=current_app.config["JUPYTERHUB_ADMIN_HEADERS"],
            )
            return res, None

        msg = []
        if not self._project_exists():
            msg.append(f"the project {self.project} does not exist")
        if not self._branch_exists():
            msg.append(f"the branch {self.branch} does not exist")
        if not self._commit_sha_exists():
            msg.append(f"the commit sha {self.commit_sha} does not exist")
        return (
            None,
            f"creating server {self.server_name} failed because {', '.join(msg)}",
        )

    def server_exists(self):
        return self.pod is not None

    @property
    def pod(self):
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
                self._delete_pvc()
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
                self._delete_pvc()

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

    @property
    def server_url(self):
        pod = self.pod
        url = "{jh_path_prefix}/user/{username}/{servername}/".format(
            jh_path_prefix=current_app.config.get("JUPYTERHUB_PATH_PREFIX").rstrip("/"),
            username=pod.metadata.annotations["hub.jupyter.org/username"],
            servername=pod.metadata.annotations["hub.jupyter.org/servername"],
        )
        return urljoin(current_app.config.get("JUPYTERHUB_ORIGIN"), url)

    @classmethod
    def from_pod(cls, user, pod):
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
        pods = user.pods
        pods = filter_pods_by_annotations(
            pods, {"hub.jupyter.org/servername": server_name}
        )
        if len(pods) != 1:
            return None
        pod = pods[0]
        return cls.from_pod(user, pod)

    def _create_pvc(
        self, storage_size, storage_class="default",
    ):
        """Create a PVC."""

        # check if we already have this PVC
        pvc = self.get_pvc()
        if pvc:
            # if the requested size is bigger than the original PVC, resize
            if parse_file_size(
                pvc.spec.resources.requests.get("storage")
            ) < parse_file_size(storage_size):

                pvc.spec.resources.requests["storage"] = storage_size
                self._k8s_client.patch_namespaced_persistent_volume_claim(
                    name=pvc.metadata.name, namespace=self._k8s_namespace, body=pvc,
                )
        else:
            gl_project = self._user.gitlab_client.projects.get(
                f"{self.namespace}/{self.project}"
            )
            git_host = urlparse(current_app.config.get("GITLAB_URL")).netloc
            pvc = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(
                    name=self._pvc_name,
                    annotations={
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "git-host": git_host,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "namespace": self.namespace,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "username": self.safe_username,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "commit-sha": self.commit_sha,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "branch": self.branch,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "projectName": self.project,
                    },
                    labels={
                        "component": "singleuser-server",
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "username": self.safe_username,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "commit-sha": self.commit_sha,
                        current_app.config.get("RENKU_ANNOTATION_PREFIX")
                        + "gitlabProjectId": str(gl_project.id),
                    },
                ),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=["ReadWriteOnce"],
                    volume_mode="Filesystem",
                    storage_class_name=storage_class,
                    resources=V1ResourceRequirements(
                        requests={"storage": storage_size}
                    ),
                ),
            )
            self._k8s_client.create_namespaced_persistent_volume_claim(
                self._k8s_namespace, pvc
            )
        return pvc

    def _delete_pvc(self):
        """Delete a specified PVC."""
        pvc = self.get_pvc()
        if pvc:
            self._k8s_client.delete_namespaced_persistent_volume_claim(
                name=pvc.metadata.name, namespace=self._k8s_namespace
            )
            current_app.logger.debug(f"pvc deleted: {pvc.metadata.name}")

    def get_pvc(self):
        """Fetch the PVC for the given username, project, commit combination."""
        try:
            return self._k8s_client.read_namespaced_persistent_volume_claim(
                self._pvc_name, self._k8s_namespace
            )
        except client.ApiException:
            return None

    @property
    def _pvc_name(self):
        """Form a PVC name from a username and servername."""
        return f"{self.safe_username}-{self.namespace}-{self.server_name}-pvc"
