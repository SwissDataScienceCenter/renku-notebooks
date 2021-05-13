from flask import current_app
from kubernetes import client
from kubernetes.client.models.v1_resource_requirements import V1ResourceRequirements
import requests
import re
from urllib.parse import urlparse

from ...util.kubernetes_ import get_k8s_client
from ...util.file_size import parse_file_size


class Autosave:
    def __init__(self, user, namespace, project, root_commit_sha):
        self.user = user
        self.namespace = namespace
        self.project = project
        self.root_commit_sha = root_commit_sha
        self.gl_project = self.user.get_renku_project(
            f"{self.namespace}/{self.project}"
        )
        if self.gl_project is None:
            raise ValueError(f"Project {self.namespace}/{self.project} does not exist.")
        self.gl_root_commit = self.gl_project.commits.get(self.root_commit_sha)
        if self.gl_root_commit is None:
            raise ValueError(
                f"Commit {self.root_commit_sha} for project "
                f"{self.namespace}/{self.project} does not exist."
            )

    def _root_commit_is_parent_of(self, commit_sha):
        res = requests.get(
            headers={"Authorization": f"Bearer {self.user.oauth_token}"},
            url=f"{current_app.config['GITLAB_URL']}/api/v4/"
            f"projects/{self.gl_project.id}/repository/merge_base",
            params={"refs[]": [self.root_commit_sha, commit_sha]},
        )
        if res.status_code == 200 and res.json().get("id") == self.root_commit_sha:
            return True
        else:
            return False

    def cleanup(self, session_commit_sha):
        if self._root_commit_is_parent_of(session_commit_sha):
            self.delete()


class BranchAutosave(Autosave):
    branch_name_regex = (
        r"^renku/autosave/(?P<username>[^/]+)/(?P<branch>.+)/"
        r"(?P<root_commit_sha>[a-zA-Z0-9]{40})/(?P<final_commit_sha>[a-zA-Z0-9]{40})$"
    )

    def __init__(self, user, namespace, project, root_commit_sha, final_commit_sha):
        super().__init__(user, namespace, project, root_commit_sha)
        self.final_commit_sha = final_commit_sha
        if self.final_commit_sha is None:
            raise ValueError("Final commit sha for PVC autosave cannot be None.")

    @property
    def exists(self):
        return self.branch is not None

    def delete(self):
        if self.exists:
            self.gl_project.branches.delete(self.branch.name)

    @property
    def branch(self):
        for branch in self.gl_project.branches.list(all=True, as_list=False):
            match_res = re.match(self.branch_name_regex, branch.name)
            if (
                match_res is not None
                and match_res.group("username") == self.user
                and match_res.group("root_commit_sha") == self.root_commit_sha
                and match_res.group("final_commit_sha") == self.final_commit_sha
            ):
                return branch
        return None

    @classmethod
    def from_branch_name(cls, user, project_name, branch_name):
        match_res = re.match(cls.branch_name_regex, branch_name)
        if match_res is None:
            raise ValueError("Invalid branch name for autosave branch.")
        return cls(
            user,
            match_res.group("namespace"),
            project_name,
            match_res.group("root_commit_sha"),
            match_res.group("final_commit_sha"),
        )


class SessionPVC(Autosave):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        k8s_client, k8s_namespace = get_k8s_client()
        self.k8s_client = k8s_client
        self.k8s_namespace = k8s_namespace

    @property
    def exists(self):
        return self.pvc is not None

    def delete(self):
        if self.exists and not self.is_mounted:
            self.k8s_client.delete_namespaced_persistent_volume_claim(
                name=self.pvc.metadata.name, namespace=self.k8s_namespace
            )

    def create(self, storage_size, storage_class):
        # check if we already have this PVC
        pvc = self.pvc
        if pvc is not None:
            # if the requested size is bigger than the original PVC, resize
            if parse_file_size(
                pvc.spec.resources.requests.get("storage")
            ) < parse_file_size(storage_size):

                pvc.spec.resources.requests["storage"] = storage_size
                self._k8s_client.patch_namespaced_persistent_volume_claim(
                    name=pvc.metadata.name, namespace=self._k8s_namespace, body=pvc,
                )
        else:
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
                        + "gitlabProjectId": str(self.gl_project.id),
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
            self.k8s_client.create_namespaced_persistent_volume_claim(
                self.k8s_namespace, pvc
            )

    @property
    def pvc(self):
        res = [
            pvc
            for pvc in self.user._get_pvcs()
            if pvc.metadata.annotations.get(
                current_app.config.get("RENKU_ANNOTATION_PREFIX") + "projectName"
            )
            == self.project
            and pvc.metadata.annotations.get(
                current_app.config.get("RENKU_ANNOTATION_PREFIX") + "commit-sha"
            )
            == self.root_commit_sha
        ]
        if len(res) == 1:
            return res[0]
        return None

    @property
    def is_mounted(self):
        for pod in self.user.pods:
            for volume in pod.spec.volumes:
                pvc = volume.persistent_volume_claim
                if pvc.metadata.name == self.pvc.metadata.name:
                    return True
        return False

    @classmethod
    def from_pvc(cls, user, pvc):
        namespace = pvc.metadata.annotations.get(
            current_app.config.get("RENKU_ANNOTATION_PREFIX") + "namespace"
        )
        project = pvc.metadata.annotations.get(
            current_app.config.get("RENKU_ANNOTATION_PREFIX") + "projectName"
        )
        root_commit_sha = pvc.metadata.annotations.get(
            current_app.config.get("RENKU_ANNOTATION_PREFIX") + "commit-sha"
        )
        parameters_missing = [
            namespace is None,
            project is None,
            root_commit_sha is None,
        ]
        if any(parameters_missing):
            raise ValueError(
                "Required PVC annotations for creating SessionPVC are missing."
            )
        return cls(user, namespace, project, root_commit_sha)
