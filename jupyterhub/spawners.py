# -*- coding: utf-8 -*-
#
# Copyright 2018 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Implement integration for using GitLab repositories."""

import os
from urllib.parse import urlsplit, urlunsplit, urlparse

import escapism
import gitlab
from kubernetes import client
from tornado import gen, web
from urllib3.exceptions import ProtocolError

from kubespawner import KubeSpawner

RENKU_ANNOTATION_PREFIX = "renku.io/"
"""The prefix for renku-specific pod annotations."""

# Do we have access to the JH config directly in the spawner?
GITLAB_AUTH = os.environ.get("JUPYTERHUB_AUTHENTICATOR", "gitlab") == "gitlab"


class SpawnerMixin:
    """Extend spawner methods."""

    @gen.coroutine
    def git_repository(self):
        """Return the URL of current repository."""
        options = self.user_options
        namespace = options.get("namespace")
        project = options.get("project")

        url = os.environ.get("GITLAB_URL", "http://gitlab.renku.build")

        scheme, netloc, path, query, fragment = urlsplit(url)

        repository = urlunsplit(
            (
                scheme,
                netloc,
                path + "/" + namespace + "/" + project + ".git",
                query,
                fragment,
            )
        )

        return repository

    def get_env(self):
        """Extend environment variables passed to the notebook server."""
        # TODO how to get the async result here?
        #      repository = yield from self.git_repository()

        environment = super().get_env()

        env_dict = {
            "CI_NAMESPACE": self.user_options.get("namespace", ""),
            "CI_PROJECT": self.user_options.get("project", ""),
            "CI_COMMIT_SHA": self.user_options.get("commit_sha", ""),
            "GITLAB_URL": os.environ.get("GITLAB_URL", "http://gitlab.renku.build"),
            "CI_REF_NAME": self.user_options.get("branch", "master"),
        }

        if GITLAB_AUTH:
            env_dict.update(
                {
                    "EMAIL": self.gl_user.email,
                    "GIT_AUTHOR_NAME": self.gl_user.name,
                    "GIT_COMMITTER_NAME": self.gl_user.name,
                }
            )

        environment.update(env_dict)
        return environment

    @gen.coroutine
    def start(self, *args, **kwargs):
        """Start the notebook server."""
        self.log.info("starting with args: {}".format(" ".join(self.get_args())))
        self.log.debug("user options: {}".format(self.user_options))

        auth_state = yield self.user.get_auth_state()
        if GITLAB_AUTH:
            assert "access_token" in auth_state
            oauth_token = auth_state["access_token"]
        else:
            oauth_token = None

        options = self.user_options
        namespace = options.get("namespace")
        project = options.get("project")
        self.image = options.get("image")
        self.cmd = "jupyterhub-singleuser"

        url = os.getenv("GITLAB_URL", "http://gitlab.renku.build")

        gl = gitlab.Gitlab(url, api_version=4, oauth_token=oauth_token)
        gl_project = gl.projects.get("{0}/{1}".format(namespace, project))

        self.environment["GITLAB_AUTOSAVE"] = "0"

        # check authorization against GitLab
        if GITLAB_AUTH:
            try:
                gl.auth()
                self.gl_user = gl.user

            except Exception as e:
                self.log.error(e)
                raise web.HTTPError(401, "Not logged in with GitLab.")

            # gather project permissions for the logged in user
            permissions = gl_project.attributes["permissions"].items()
            access_levels = [x[1].get("access_level", 0) for x in permissions if x[1]]
            access_levels_string = ", ".join(map(lambda lev: str(lev), access_levels))

            self.log.debug(
                "access level for user {username} in "
                "{namespace}/{project} = {access_level}".format(
                    username=self.user.name,
                    namespace=namespace,
                    project=project,
                    access_level=access_levels_string,
                )
            )

            access_level = gitlab.GUEST_ACCESS
            if len(access_levels) > 0:
                access_level = max(access_levels)
            self.gl_access_level = access_level

            if access_level >= gitlab.MAINTAINER_ACCESS:

                environment = {
                    variable.key: variable.value
                    for variable in gl_project.variables.list()
                }
                self.environment.update(environment)

            if access_level >= gitlab.DEVELOPER_ACCESS:
                self.environment["GITLAB_AUTOSAVE"] = "1"

        try:
            result = yield super().start(*args, **kwargs)
        except ProtocolError:
            self.log.warning(
                "Spawning a JH server failed with ProtocolError, "
                f"user_options {self.user_options}, args: {' '.join(self.get_args())}, "
                f"auth_state has keys: {list(auth_state.keys())}, "
                f"oauth_token is None: {oauth_token is None}"
            )
            raise
        return result


class RenkuKubeSpawner(SpawnerMixin, KubeSpawner):
    """A class for spawning notebooks on Renku-JupyterHub using K8S."""

    @gen.coroutine
    def get_pod_manifest(self):
        """Include volume with the git repository."""
        repository = yield self.git_repository()
        options = self.user_options
        auth_state = yield self.user.get_auth_state()
        self.extra_containers = []

        if GITLAB_AUTH:
            assert "access_token" in auth_state
            oauth_token = auth_state["access_token"]
        else:
            oauth_token = None

        # make sure the pod name is less than 64 characters - if longer, keep
        # the last 16 untouched since it is the server hash
        if len(self.pod_name) > 63:
            self.pod_name = self.pod_name[:47] + self.pod_name[-16:]

        # Process the requested server options
        server_options = options.get("server_options", {})
        self.default_url = server_options.get("defaultUrl")
        self.cpu_guarantee = float(server_options.get("cpu_request", 0.1))

        # Make the user pods be in Guaranteed QoS class if the user
        # had specified a memory request. Otherwise use a sensible default.
        self.mem_guarantee = server_options.get("mem_request", "500M")
        self.mem_limit = server_options.get("mem_request", "1G")

        gpu = server_options.get("gpu_request", {})
        if gpu:
            self.extra_resource_limits = {"nvidia.com/gpu": str(gpu)}

        # Configure the git repository volume
        git_volume_name = self.pod_name[:54] + "-git-repo"

        # 1. Define the volume.
        self.volumes = [
            volume for volume in self.volumes if volume["name"] != git_volume_name
        ]
        if not options.get("pvc_name"):
            volume = {"name": git_volume_name, "emptyDir": {}}
        else:
            volume = {
                "name": git_volume_name,
                "persistentVolumeClaim": {"claimName": options.get("pvc_name")},
            }
        self.volumes.append(volume)

        # 2. Define a volume mount for both init and notebook containers.
        mount_path = f'/work/{options["project"]}'
        volume_mount = {"mountPath": mount_path, "name": git_volume_name}

        # 3. Configure the init container
        init_container_name = "git-clone"
        self.init_containers = [
            container
            for container in self.init_containers
            if not container.name.startswith(init_container_name)
        ]
        lfs_auto_fetch = server_options.get("lfs_auto_fetch")
        gitlab_autosave = self.environment.get("GITLAB_AUTOSAVE", "0")
        init_container = client.V1Container(
            name=init_container_name,
            env=[
                client.V1EnvVar(name="MOUNT_PATH", value=mount_path),
                client.V1EnvVar(name="REPOSITORY", value=repository),
                client.V1EnvVar(
                    name="LFS_AUTO_FETCH", value="1" if lfs_auto_fetch else "0"
                ),
                client.V1EnvVar(
                    name="COMMIT_SHA", value=str(options.get("commit_sha"))
                ),
                client.V1EnvVar(name="BRANCH", value=options.get("branch", "master")),
                client.V1EnvVar(name="JUPYTERHUB_USER", value=self.user.name),
                client.V1EnvVar(name="GITLAB_AUTOSAVE", value=gitlab_autosave),
                client.V1EnvVar(name="GITLAB_OAUTH_TOKEN", value=oauth_token),
                client.V1EnvVar(name="GITLAB_URL", value=os.getenv("GITLAB_URL")),
                client.V1EnvVar(
                    name="PVC_EXISTS", value=str(options.get("pvc_exists"))
                ),
            ],
            image=options.get("git_clone_image"),
            volume_mounts=[volume_mount],
            working_dir=mount_path,
            security_context=client.V1SecurityContext(run_as_user=0),
        )
        self.init_containers.append(init_container)

        # 4. Configure notebook container git repo volume mount
        self.volume_mounts = [
            volume_mount
            for volume_mount in self.volume_mounts
            if volume_mount["mountPath"] != mount_path
        ]
        self.volume_mounts.append(volume_mount)

        # 5. Autosaving script should operate regardless of whether a PVC is used or not.
        # This is the only way to save un-pushed commits after a user shuts down a session.
        self.lifecycle_hooks = {
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
        }

        # 6. Set up the https proxy for GitLab
        https_proxy = client.V1Container(
            name="git-https-proxy",
            env=[
                client.V1EnvVar(name="GITLAB_OAUTH_TOKEN", value=oauth_token),
                client.V1EnvVar(name="REPOSITORY_URL", value=repository),
                client.V1EnvVar(name="MITM_PROXY_PORT", value="8080"),
            ],
            image=options.get("git_https_proxy_image"),
        )
        self.extra_containers.append(https_proxy)

        # Finalize the pod configuration

        # Set the repository path to the working directory
        self.working_dir = mount_path
        self.notebook_dir = mount_path

        # add git project-specific annotations
        repository_url = (
            os.environ.get("GITLAB_URL", "http://gitlab.renku.build")
            + "/"
            + options.get("namespace")
            + "/"
            + options.get("project")
        )
        parsed_git_url = urlparse(
            os.environ.get("GITLAB_URL", "http://gitlab.renku.build")
        )
        git_host = parsed_git_url.netloc
        safe_username = escapism.escape(self.user.name, escape_char="-").lower()
        self.extra_annotations = {
            RENKU_ANNOTATION_PREFIX + "namespace": options.get("namespace"),
            RENKU_ANNOTATION_PREFIX
            + "gitlabProjectId": "{}".format(options.get("project_id")),
            RENKU_ANNOTATION_PREFIX + "branch": options.get("branch"),
            RENKU_ANNOTATION_PREFIX + "repository": repository_url,
            RENKU_ANNOTATION_PREFIX + "git-host": git_host,
            RENKU_ANNOTATION_PREFIX + "username": safe_username,
            RENKU_ANNOTATION_PREFIX + "commit-sha": options.get("commit_sha"),
            RENKU_ANNOTATION_PREFIX + "projectName": options.get("project"),
        }
        # some annotations are repeated as labels so that the k8s api can filter resources
        self.extra_labels = {
            RENKU_ANNOTATION_PREFIX + "username": safe_username,
            RENKU_ANNOTATION_PREFIX + "commit-sha": options.get("commit_sha"),
            RENKU_ANNOTATION_PREFIX
            + "gitlabProjectId": "{}".format(options.get("project_id")),
            "hub.jupyter.org/network-access-hub": "true",
        }

        self.delete_grace_period = 30

        self.gid = 100
        self.supplemental_gids = [1000]

        # set the image pull policy
        self.image_pull_policy = "Always"

        # Prevent kubernetes service links from appearing in user environment
        self.extra_pod_config = {"enableServiceLinks": False}

        pod = yield super().get_pod_manifest()

        # Because repository comes from a coroutine, we can't put it simply in `get_env()`
        pod.spec.containers[0].env.append(
            client.V1EnvVar("CI_REPOSITORY_URL", repository)
        )

        # Add image pull secrets
        if options.get("image_pull_secrets"):
            secrets = [
                client.V1LocalObjectReference(name=name)
                for name in options.get("image_pull_secrets")
            ]
            pod.spec.image_pull_secrets = secrets

        return pod
