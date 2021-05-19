import escapism
from flask import current_app
import gitlab
from kubernetes import client
import re

from ...util.kubernetes_ import get_k8s_client
from .storage import AutosaveBranch, SessionPVC


class User:
    reqd_auth_headers = [
        "Renku-Auth-Access-Token",
        "Renku-Auth-Id-Token",
        "Renku-Auth-Git-Credentials",
    ]

    def __init__(self, auth_headers):
        if self._validate_header_keys(auth_headers) is None:
            return None
        # TODO: Ensure that headers are valid - or does the gateway take care of this?
        self.git_url, self.git_credentials = next(
            iter(auth_headers["Renku-Auth-Git-Credentials"].items())
        )
        self.git_token = re.match(
            r"^[^\s]+\ ([^\s]+)$", self.git_credentials["AuthorizationHeader"]
        ).group(1)
        self.gitlab_client = gitlab.Gitlab(
            self.git_url, api_version=4, oauth_token=self.git_token,
        )
        self.gitlab_client.auth()
        self.username = self.gitlab_client.user.username
        self.safe_username = (escapism.escape(self.username, escape_char="-").lower())
        self.keycloak_id_token = auth_headers["Renku-Auth-Id-Token"]
        self.keycloak_access_token = auth_headers["Renku-Auth-Access-Token"]

    def _validate_header_keys(self, auth_headers):
        """Confirm that the app configuration contains the minimum required
        parameters needed for the handling users."""
        for header_key in self.reqd_auth_headers:
            if header_key not in auth_headers:
                return None
    
    def _parse_headers(self, auth_headers):
        output = {}
        output[""]

    @property
    def pods(self):
        """Get a list of k8s pod objects for all the active servers of a user."""
        k8s_client, k8s_namespace = get_k8s_client()
        pods = k8s_client.list_namespaced_pod(
            k8s_namespace,
            label_selector=f"heritage=jupyterhub,renku.io/username={self.safe_username}",
        )
        return pods.items

    def get_autosaves(self, namespace_project=None):
        """Get a list of autosaves for all projects for the user"""
        autosaves = []
        # add pvcs to list of autosaves only if pvcs are supported in deployment
        if current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]:
            if namespace_project is None:
                autosaves += [
                    SessionPVC.from_pvc(self, pvc) for pvc in self._get_pvcs()
                ]
            else:
                project_name_annotation_key = (
                    current_app.config.get("RENKU_ANNOTATION_PREFIX") + "projectName"
                )
                autosaves += [
                    SessionPVC.from_pvc(self, pvc)
                    for pvc in self._get_pvcs()
                    if pvc.metadata.annotations.get(project_name_annotation_key)
                    == namespace_project.split("/")[-1]
                ]
        # add any autosave branches, regardless of wheter pvcs are supported or not
        if namespace_project is None:  # get autosave branches from all projects
            projects = self.gitlab_client.projects.list()
        else:
            projects = [self.get_renku_project(namespace_project)]
        for project in projects:
            for branch in project.branches.list():
                if re.match(r"^renku\/autosave\/", branch.name) is not None:
                    autosaves.append(
                        AutosaveBranch.from_branch_name(
                            self, namespace_project, branch.name
                        )
                    )
        return autosaves

    def _get_pvcs(self):
        """Get all session pvcs that belong to this user"""
        if not current_app.config["NOTEBOOKS_SESSION_PVS_ENABLED"]:
            return []
        else:
            k8s_client, k8s_namespace = get_k8s_client()
            label_selector = ",".join(
                [
                    "component=singleuser-server",
                    current_app.config.get("RENKU_ANNOTATION_PREFIX")
                    + "username="
                    + self.safe_username,
                ]
            )
            try:
                return k8s_client.list_namespaced_persistent_volume_claim(
                    k8s_namespace, label_selector=label_selector
                ).items
            except client.ApiException:
                return []

    def get_renku_project(self, namespace_project):
        """Retrieve the GitLab project."""
        try:
            return self.gitlab_client.projects.get("{0}".format(namespace_project))
        except Exception as e:
            current_app.logger.error(
                f"Cannot get project: {namespace_project} for user: {self.hub_username}, error: {e}"
            )
