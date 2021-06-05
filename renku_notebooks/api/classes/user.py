import escapism
from flask import current_app
import gitlab
from kubernetes import client
import re
import json
import base64

from ...util.kubernetes_ import get_k8s_client
from .storage import AutosaveBranch


class User:
    reqd_auth_headers = [
        "Renku-Auth-Access-Token",
        "Renku-Auth-Id-Token",
        "Renku-Auth-Git-Credentials",
    ]

    def __init__(self, auth_headers):
        self.logged_in = False
        for header_key in self.reqd_auth_headers:
            if header_key not in auth_headers:
                return  # user is not logged in
        self._parse_headers(auth_headers)
        self.gitlab_client = gitlab.Gitlab(
            self.git_url, api_version=4, oauth_token=self.git_token,
        )
        self.gitlab_client.auth()
        self.username = self.gitlab_client.user.username
        self.safe_username = escapism.escape(self.username, escape_char="-").lower()
        self.logged_in = True
        self._k8s_client, self._k8s_namespace = get_k8s_client()
        self._k8s_api_instance = client.CustomObjectsApi(client.ApiClient())

    def _parse_headers(self, auth_headers):
        def get_git_creds(auth_headers):
            parsed_dict = json.loads(
                base64.decodebytes(auth_headers["Renku-Auth-Git-Credentials"].encode())
            )
            git_url, git_credentials = next(iter(parsed_dict.items()))
            token_match = re.match(
                r"^[^\s]+\ ([^\s]+)$", git_credentials["AuthorizationHeader"]
            )
            git_token = token_match.group(1) if token_match is not None else None
            return git_url, git_credentials["AuthorizationHeader"], git_token

        def parse_jwt_payload(jwt):
            return json.loads(base64.b64decode(jwt.split(".")[1].encode() + b"=="))

        parsed_id_token = parse_jwt_payload(auth_headers["Renku-Auth-Id-Token"])
        self.keycloak_user_id = parsed_id_token["sub"]
        self.email = parsed_id_token["email"]
        self.oidc_issuer = parsed_id_token["iss"]
        self.git_url, self.git_auth_header, self.git_token = get_git_creds(auth_headers)

    @property
    def crds(self):
        """Get a list of k8s pod objects for all the active servers of a user."""
        label_selector = (
            f"{current_app.config['RENKU_ANNOTATION_PREFIX']}"
            f"safe-username={self.safe_username}"
        )
        crds = self._k8s_api_instance.list_namespaced_custom_object(
            group=current_app.config["CRD_GROUP"],
            version=current_app.config["CRD_VERSION"],
            namespace=self._k8s_namespace,
            plural=current_app.config["CRD_PLURAL"],
            label_selector=label_selector,
        )
        return crds["items"]

    def get_autosaves(self, namespace_project=None):
        """Get a list of autosaves for all projects for the user"""
        gl_project = (
            self.get_renku_project(namespace_project)
            if namespace_project is not None
            else None
        )
        autosaves = []
        # add any autosave branches, regardless of wheter pvcs are supported or not
        if namespace_project is None:  # get autosave branches from all projects
            projects = self.gitlab_client.projects.list()
        else:
            projects = [gl_project]
        for project in projects:
            for branch in project.branches.list():
                if re.match(r"^renku\/autosave\/" + self.username, branch.name) is not None:
                    autosaves.append(
                        AutosaveBranch.from_branch_name(
                            self, namespace_project, branch.name
                        )
                    )
        return autosaves

    def get_renku_project(self, namespace_project):
        """Retrieve the GitLab project."""
        try:
            return self.gitlab_client.projects.get("{0}".format(namespace_project))
        except Exception as e:
            current_app.logger.error(
                f"Cannot get project: {namespace_project} for user: {self.username}, error: {e}"
            )
