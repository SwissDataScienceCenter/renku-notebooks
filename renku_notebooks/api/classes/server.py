from flask import current_app
from kubernetes import client
from kubernetes.client.rest import ApiException
import base64
import json
from urllib.parse import urlparse
from urllib.parse import urljoin


from ...util.check_image import parse_image_name, get_docker_token, image_exists
from ...util.kubernetes_ import (
    get_k8s_client,
    filter_resources_by_annotations,
    make_server_name,
)


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
        self._k8s_api_instance = client.CustomObjectsApi(client.ApiClient())
        self.safe_username = self._user.safe_username
        self.namespace = namespace
        self.project = project
        self.branch = branch
        self.commit_sha = commit_sha
        self.notebook = notebook
        self.image = image
        self.server_options = server_options
        self.using_default_image = self.image == current_app.config.get("DEFAULT_IMAGE")
        self.git_host = urlparse(current_app.config["GITLAB_URL"]).netloc

    def _check_flask_config(self):
        """Check the app config and ensure minimum required parameters are present."""
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
                    "Password": self._user.git_token,
                    "Email": self._user.email,
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
        verified_image, is_image_private = self._get_image(self.image)
        extra_resources = []
        stateful_set_image_pull_secret_modifications = []
        stateful_set_container_modifications = []
        # Add labels and annotations - applied to overall manifest and secret only
        labels = {
            "app": "jupyterhub",
            "component": "singleuser-server",
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}commit-sha": self.commit_sha,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}gitlabProjectId": str(
                gl_project.id
            ),
            current_app.config["RENKU_ANNOTATION_PREFIX"]
            + "safe-username": self._user.safe_username,
        }
        annotations = {
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}commit-sha": self.commit_sha,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}gitlabProjectId": str(
                gl_project.id
            ),
            current_app.config["RENKU_ANNOTATION_PREFIX"]
            + "safe-username": self._user.safe_username,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}username": self._user.username,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}servername": self.server_name,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}branch": self.branch,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}git-host": self.git_host,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}namespace": gl_project.namespace[
                "full_path"
            ],
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}projectName": gl_project.name.lower(),
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}requested-image": self.image,
        }
        # Add image pull secret if image is private
        if is_image_private:
            image_pull_secret_name = self.server_name + "-secret"
            extra_resources.append(
                {
                    "api": "CoreV1Api",
                    "creationMethod": "create_namespaced_secret",
                    "resourceSpec": {
                        "apiVersion": "v1",
                        "data": {".dockerconfigjson": self._get_registry_secret()},
                        "kind": "Secret",
                        "metadata": {
                            "name": image_pull_secret_name,
                            "namespace": self._k8s_namespace,
                            "labels": labels,
                            "annotations": annotations,
                        },
                        "type": "kubernetes.io/dockerconfigjson",
                    },
                }
            )
            stateful_set_image_pull_secret_modifications.append(
                {"name": image_pull_secret_name}
            )
        # Add git init / sidecar container
        stateful_set_container_modifications.append(
            {
                "image": "ableuler/py-git:latest",
                "name": "git-sidecar",
                "ports": [
                    {"containerPort": 4000, "name": "git-port", "protocol": "TCP"}
                ],
                "env": [
                    {
                        "name": "MOUNT_PATH",
                        # Folder name is the same as what was provdied in
                        # url for cloning. Gitlab keeps case (upper/lower)
                        # in project.name but not in
                        # project.http_url_to_repo so the folder for the
                        # project is always lowercase
                        "value": f"/work/{gl_project.name.lower()}",
                    },
                    {"name": "REPOSITORY", "value": gl_project.http_url_to_repo},
                    {
                        "name": "LFS_AUTO_FETCH",
                        "value": "1" if self.server_options["lfs_auto_fetch"] else "0",
                    },
                    {"name": "COMMIT_SHA", "value": self.commit_sha},
                    {"name": "BRANCH", "value": "master"},
                    {
                        # used only for naming autosave branch
                        "name": "JUPYTERHUB_USER",
                        "value": self._user.username,
                    },
                    {"name": "GIT_AUTOSAVE", "value": "1"},
                    {"name": "GIT_URL", "value": current_app.config["GITLAB_URL"]},
                ],
                "resources": {},
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "fsGroup": 100,
                    "runAsGroup": 100,
                    "runAsUser": 1000,
                },
                "volumeMounts": [
                    {"mountPath": "/work", "name": "workspace", "subPath": "work"}
                ],
            }
        )
        # Add git proxy container
        stateful_set_container_modifications.append(
            {
                "image": "ableuler/git-proxy:latest",
                "name": "git-proxy",
                "env": [
                    {"name": "GITLAB_OAUTH_TOKEN", "value": self._user.git_token},
                    {"name": "REPOSITORY_URL", "value": gl_project.http_url_to_repo},
                    {"name": "MITM_PROXY_PORT", "value": "8080"},
                ],
            }
        )
        resource_modifications = [
            {
                "modification": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": stateful_set_container_modifications,
                                "imagePullSecrets": stateful_set_image_pull_secret_modifications,
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
        manifest = {
            "apiVersion": f"{current_app.config['CRD_GROUP']}/{current_app.config['CRD_VERSION']}",
            "kind": "JupyterServer",
            "metadata": {
                "name": self.server_name,
                "labels": labels,
                "annotations": annotations,
            },
            "spec": {
                "auth": {
                    "cookieWhiteList": ["username-localhost-8888", "_xsrf"],
                    "token": "mysecrettoken",
                    "oidc": {
                        "enabled": False,
                        # "clientId": current_app.config["OIDC_CLIENT_ID"],
                        # "clientSecret": current_app.config["OIDC_CLIENT_SECRET"],
                        # "issuerUrl": self._user.oidc_issuer,
                        # "userId": self._user.keycloak_user_id,
                    },
                },
                "extraResources": extra_resources,
                "jupyterServer": {
                    "defaultUrl": self.server_options["defaultUrl"],
                    "image": verified_image,
                    "rootDir": "/home/jovyan/work/",
                },
                "resourceModifications": resource_modifications,
                "routing": {
                    "host": current_app.config["SESSIONS_HOST"],
                    "path": f"/sessions/{self.server_name}",
                },
                "volume": {
                    "size": self.server_options["disk_request"],
                    "storageClass": current_app.config[
                        "NOTEBOOKS_SESSION_PVS_STORAGE_CLASS"
                    ],
                },
            },
        }
        return manifest

    def start(self):
        """Create the jupyterserver crd in k8s."""
        if (
            self._project_exists()
            and self._branch_exists()
            and self._commit_sha_exists()
        ):
            try:
                crd = self._k8s_api_instance.create_namespaced_custom_object(
                    group=current_app.config["CRD_GROUP"],
                    version=current_app.config["CRD_VERSION"],
                    namespace=self._k8s_namespace,
                    plural=current_app.config["CRD_PLURAL"],
                    body=self._get_session_manifest(),
                )
            except ApiException as e:
                current_app.logger.debug(
                    f"Cannot start the session {self.server_name}, error: {e}"
                )
                return None
            else:
                return crd

    def server_exists(self):
        """Check if the user server exists (i.e. is an actual pod in k8s)."""
        return self.crd is not None

    @property
    def crd(self):
        """Get the crd of the user jupyter user session from k8s."""
        crds = filter_resources_by_annotations(
            self._user.crds,
            {
                f"{current_app.config['RENKU_ANNOTATION_PREFIX']}servername": self.server_name
            },
        )
        if len(crds) == 0:
            return None
        elif len(crds) == 1:
            return crds[0]
        else:  # more than one pod was matched
            raise Exception(
                f"The user session matches {len(crds)} k8s pods, "
                "it should match only one."
            )

    @property
    def pod(self):
        """Get the pod of the jupyter user session"""
        # TODO: Add user to child crd resources labels and add user here
        res = self._k8s_client.list_namespaced_pod(
            self._k8s_namespace, label_selector=f"app={self.server_name}"
        )
        current_app.logger.debug(f"Finding pod wiht selector app={self.server_name}, {res}")
        if len(res.items) == 1:
            return res.items[0]
        else:
            return None

    def stop(self, forced=False):
        """Stop user's server with specific name"""
        try:
            status = self._k8s_api_instance.delete_namespaced_custom_object(
                group=current_app.config["CRD_GROUP"],
                version=current_app.config["CRD_VERSION"],
                namespace=self._k8s_namespace,
                plural=current_app.config["CRD_PLURAL"],
                name=self.server_name,
                grace_period_seconds=0 if forced else None,
            )
        except ApiException as e:
            current_app.logger.warning(
                f"Cannot delete server: {self.server_name} for user: "
                f"{self._user.username}, error: {e}"
            )
            return None
        else:
            return status

    def get_logs(self, max_log_lines=0, container_name="jupyter-server"):
        """Get the logs of the k8s pod that runs the user server."""
        pod = self.pod
        if pod is None:
            return None
        pod_name = pod.metadata.name
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
        """The URL where a user can access their session."""
        return urljoin(
            "https://" + current_app.config["SESSIONS_HOST"], self.server_name
        )

    @classmethod
    def from_crd(cls, user, crd):
        """Create a Server instance from a k8s pod object."""
        return cls(
            user,
            crd["metadata"]["annotations"].get(
                current_app.config["RENKU_ANNOTATION_PREFIX"] + "namespace"
            ),
            crd["metadata"]["annotations"].get(
                current_app.config["RENKU_ANNOTATION_PREFIX"] + "projectName"
            ),
            crd["metadata"]["annotations"].get(
                current_app.config["RENKU_ANNOTATION_PREFIX"] + "branch"
            ),
            crd["metadata"]["annotations"].get(
                current_app.config["RENKU_ANNOTATION_PREFIX"] + "commit-sha"
            ),
            None,
            crd["metadata"]["annotations"].get(
                current_app.config["RENKU_ANNOTATION_PREFIX"] + "requested-image"
            ),
            {},  # TODO: properly parse server options from manifest
        )

    @classmethod
    def from_server_name(cls, user, server_name):
        """Create a Server instance from a Jupyterhub server name."""
        crds = user.crds
        crds = filter_resources_by_annotations(
            crds,
            {f"{current_app.config['RENKU_ANNOTATION_PREFIX']}servername": server_name},
        )
        if len(crds) != 1:
            return None
        crd = crds[0]
        return cls.from_crd(user, crd)
