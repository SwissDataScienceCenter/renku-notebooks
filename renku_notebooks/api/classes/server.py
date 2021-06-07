from flask import current_app
import gitlab
from kubernetes import client
from kubernetes.client.rest import ApiException
import base64
import json
from urllib.parse import urlparse, urljoin


from ...util.check_image import parse_image_name, get_docker_token, image_exists
from ...util.kubernetes_ import (
    get_k8s_client,
    filter_resources_by_annotations,
    make_server_name,
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
        self._crd_frozen = False
        self._last_crd = None
        try:
            self.gl_project = self._user.get_renku_project(
                f"{self.namespace}/{self.project}"
            )
        except Exception:
            self.gl_project = None

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

    @property
    def autosave_allowed(self):
        allowed = False
        if self._user.logged_in:
            # gather project permissions for the logged in user
            permissions = self.gl_project.attributes["permissions"].items()
            access_levels = [x[1].get("access_level", 0) for x in permissions if x[1]]
            access_levels_string = ", ".join(map(lambda lev: str(lev), access_levels))
            current_app.logger.debug(
                "access level for user {username} in "
                "{namespace}/{project} = {access_level}".format(
                    username=self._user.username,
                    namespace=self.namespace,
                    project=self.project,
                    access_level=access_levels_string,
                )
            )
            access_level = gitlab.GUEST_ACCESS
            if len(access_levels) > 0:
                access_level = max(access_levels)
            if access_level >= gitlab.DEVELOPER_ACCESS:
                allowed = True

        return allowed

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
        if image is None:
            parsed_image = {
                "hostname": current_app.config.get("IMAGE_REGISTRY"),
                "image": self.gl_project.path_with_namespace.lower(),
                "tag": self.commit_sha[:7],
            }
            commit_image = (
                f"{current_app.config.get('IMAGE_REGISTRY')}/"
                f"{self.gl_project.path_with_namespace.lower()}"
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

    def _get_session_k8s_resources(self):
        cpu = float(self.server_options["cpu_request"])
        mem = self.server_options["mem_request"]
        gpu_req = self.server_options.get("gpu_request", {})
        gpu = {"nvidia.com/gpu": str(gpu_req)} if gpu_req else None
        resources = {
            "requests": {"memory": mem, "cpu": cpu},
            "limits": {"memory": mem, "cpu": cpu},
        }
        if gpu:
            resources["requests"] = {**resources["requests"], **gpu}
            resources["limits"] = {**resources["limits"], **gpu}
        if "ephemeral-storage" in self.server_options.keys():
            ephemeral_storage = (
                str(
                    round(
                        (
                            parse_file_size(self.server_options["ephemeral-storage"])
                            + 0
                            if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]
                            else parse_file_size(self.server_options["disk_request"])
                        )
                        / 1.074e9  # bytes to gibibytes
                    )
                )
                + "Gi"
            )
            resources["requests"] = {
                **resources["requests"],
                "ephemeral-storage": ephemeral_storage,
            }
            resources["limits"] = {
                **resources["limits"],
                "ephemeral-storage": ephemeral_storage,
            }
        return resources

    def _get_session_manifest(self):
        """Compose the body of the user session for the k8s operator"""
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
                self.gl_project.id
            ),
            current_app.config["RENKU_ANNOTATION_PREFIX"]
            + "safe-username": self._user.safe_username,
        }
        annotations = {
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}commit-sha": self.commit_sha,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}gitlabProjectId": str(
                self.gl_project.id
            ),
            current_app.config["RENKU_ANNOTATION_PREFIX"]
            + "safe-username": self._user.safe_username,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}username": self._user.username,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}servername": self.server_name,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}branch": self.branch,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}git-host": self.git_host,
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}namespace": self.gl_project.namespace[
                "full_path"
            ],
            current_app.config["RENKU_ANNOTATION_PREFIX"]
            + "projectName": self.gl_project.name.lower(),
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
                "image": current_app.config["GIT_SIDECAR_IMAGE"],
                "name": "git-sidecar",
                "ports": [
                    {"containerPort": 4000, "name": "git-port", "protocol": "TCP"}
                ],
                "env": [
                    {"name": "MOUNT_PATH", "value": "/work"},
                    {"name": "REPOSITORY", "value": self.gl_project.http_url_to_repo},
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
                    {
                        "name": "GIT_AUTOSAVE",
                        "value": "1" if self.autosave_allowed else "0",
                    },
                    {"name": "GIT_URL", "value": current_app.config["GITLAB_URL"]},
                    {"name": "GIT_EMAIL", "value": self._user.email},
                    {"name": "GIT_FULL_NAME", "value": self._user.full_name},
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
                "image": current_app.config["GIT_HTTPS_PROXY_IMAGE"],
                "name": "git-proxy",
                "env": [
                    {"name": "GITLAB_OAUTH_TOKEN", "value": self._user.git_token},
                    {
                        "name": "REPOSITORY_URL",
                        "value": self.gl_project.http_url_to_repo,
                    },
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
                                "volumes": [
                                    {
                                        "name": "notebook-helper-scripts-volume",
                                        "configMap": {
                                            "name": "notebook-helper-scripts",
                                            "defaultMode": 493,
                                        },
                                    }
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
            {
                "modification": {
                    "resources": self._get_session_k8s_resources(),
                    "env": [
                        {
                            "name": "GIT_AUTOSAVE",
                            "value": "1" if self.autosave_allowed else "0",
                        },
                        {
                            "name": "JUPYTERHUB_USER",
                            "value": self._user.username,
                        },
                        {
                            "name": "CI_COMMIT_SHA",
                            "value": self.commit_sha,
                        },
                    ],
                    "lifecycle": {
                        "preStop": {
                            "exec": {
                                "command": [
                                    "/bin/sh",
                                    "-c",
                                    "/usr/local/bin/pre-stop.sh",
                                    "||",
                                    "true",
                                ]
                            }
                        }
                    },
                    "volumeMounts": [
                        {
                            "mountPath": "/usr/local/bin/pre-stop.sh",
                            "name": "notebook-helper-scripts-volume",
                            "subPath": "pre-stop.sh",
                        }
                    ],
                },
                "resource": "jupyter-server",
            },
            {
                "modification": {
                    "resources": {
                        "limits": {"cpu": "200m", "memory": "64Mi"},
                        "requests": {"cpu": "50m", "memory": "32Mi"},
                    }
                },
                "resource": "auth-proxy",
            },
            {
                "modification": {
                    "resources": {
                        "limits": {"memory": "64Mi"},
                        "requests": {"memory": "32Mi"},
                    }
                },
                "resource": "cookie-cleaner",
            },
            {
                "modification": {
                    "resources": {
                        "limits": {"memory": "64Mi"},
                        "requests": {"memory": "32Mi"},
                    }
                },
                "resource": "authorization-plugin",
            },
            {
                "modification": {
                    "env": [
                        {
                            "name": "OAUTH2_PROXY_INSECURE_OIDC_ALLOW_UNVERIFIED_EMAIL",
                            "value": "true",
                        },
                    ]
                },
                "resource": "authentication-plugin",
            },
        ]
        if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]:
            storage = {
                "size": self.server_options["disk_request"],
                "pvc": {
                    "enabled": True,
                    "storageClass": current_app.config[
                        "NOTEBOOKS_SESSION_PVS_STORAGE_CLASS"
                    ],
                },
            }
        else:
            storage = {
                "size": self.server_options["disk_request"],
                "pvc": {"enabled": False},
            }
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
                    "token": "",
                    "oidc": {
                        "enabled": True,
                        "clientId": current_app.config["OIDC_CLIENT_ID"],
                        "clientSecret": current_app.config["OIDC_CLIENT_SECRET"],
                        "issuerUrl": self._user.oidc_issuer,
                        "userId": self._user.keycloak_user_id,
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
                    "host": urlparse(self.server_url).netloc,
                    "path": urlparse(self.server_url).path,
                    "ingressAnnotations": current_app.config[
                        "SESSION_INGRESS_ANNOTATIONS"
                    ],
                    "tlsSecret": current_app.config["SESSION_TLS_SECRET"],
                },
                "storage": storage,
            },
        }
        return manifest

    def start(self):
        """Create the jupyterserver crd in k8s."""
        if (
            self.gl_project is not None
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
                self._last_crd = crd
                return crd

    def server_exists(self):
        """Check if the user server exists (i.e. is an actual pod in k8s)."""
        return self.crd is not None

    @property
    def crd_frozen(self):
        return self._crd_frozen

    def freeze_crd(self):
        """Helps to avoid repeated unnecessary querying of the k8s api and race conditions
        and errors when deserializing the server object."""
        if self._last_crd is None:
            # Check if the crd is truly not there before freezing for good
            self._last_crd = self.crd
        self._crd_frozen = True
        return self

    @property
    def crd(self):
        """Get the crd of the user jupyter user session from k8s."""
        if self.crd_frozen:
            return self._last_crd
        else:
            crds = filter_resources_by_annotations(
                self._user.crds,
                {
                    f"{current_app.config['RENKU_ANNOTATION_PREFIX']}servername": self.server_name
                },
            )
            if len(crds) == 0:
                self._last_crd = None
                return None
            elif len(crds) == 1:
                self._last_crd = crds[0]
                return crds[0]
            else:  # more than one pod was matched
                raise Exception(
                    f"The user session matches {len(crds)} k8s pods, "
                    "it should match only one."
                )

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
        crd = self.crd
        if crd is None:
            return None
        pod_name = crd["children"]["Pod"]["name"]
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
            "https://" + current_app.config["SESSION_HOST"],
            f"sessions/{self.server_name}",
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
            cls._get_server_options_from_crd(crd),
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

    @staticmethod
    def _get_server_options_from_crd(crd):
        server_options = {}
        # url
        server_options["defaultUrl"] = crd["spec"]["jupyterServer"]["defaultUrl"]
        # disk
        server_options["disk_request"] = crd["spec"]["storage"]["size"]
        # cpu, memory, gpu, ephemeral storage
        k8s_res_name_xref = {
            "memory": "mem_request",
            "nvidia.com/gpu": "gpu_request",
            "cpu": "cpu_request",
            "ephemeral-storage": "ephemeral-storage",
        }
        js_resources = [
            res_mod["modification"]["resources"]["limits"]
            for res_mod in crd["spec"]["resourceModifications"]
            if res_mod["resource"] == "jupyter-server"
            and res_mod["modification"].get("resources") is not None
        ]
        if len(js_resources) == 1:
            for k8s_res_name in k8s_res_name_xref.keys():
                if k8s_res_name in js_resources[0].keys():
                    server_options[k8s_res_name_xref[k8s_res_name]] = js_resources[0][
                        k8s_res_name
                    ]
        # adjust ephemeral storage properly based on whether persistent volumes are used
        if "ephemeral-storage" in server_options.keys():
            server_options["ephemeral-storage"] = (
                str(
                    round(
                        (
                            parse_file_size(server_options["ephemeral-storage"]) - 0
                            if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]
                            else parse_file_size(server_options["disk_request"])
                        )
                        / 1.074e9  # bytes to gibibytes
                    )
                )
                + "Gi"
            )
        # lfs auto fetch
        for res_mod in crd["spec"]["resourceModifications"]:
            if res_mod["resource"] == "statefulset":
                for container_mod in res_mod["modification"]["spec"]["template"][
                    "spec"
                ]["containers"]:
                    if container_mod["name"] == "git-sidecar":
                        for env_var in container_mod["env"]:
                            if env_var["name"] == "LFS_AUTO_FETCH":
                                server_options["lfs_auto_fetch"] = (
                                    env_var["name"] == "1"
                                )
        return {
            **current_app.config["SERVER_OPTIONS_DEFAULTS"],
            **server_options,
        }
